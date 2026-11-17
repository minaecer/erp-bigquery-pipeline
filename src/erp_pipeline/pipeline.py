"""Pipeline steps. Each takes the run date as an ISO string so Airflow can pass {{ ds }} directly."""
from __future__ import annotations

import json
import logging
from datetime import date

import pandas as pd

from . import bq, config
from .checks import run_checks
from .generate_data import generate_daily
from .transform import validate

log = logging.getLogger(__name__)
TABLES = ["customers", "products", "sales_orders", "sales_lines", "fx_rates"]
SQL_STEPS = ["00_ddl.sql", "10_dim_customer.sql", "11_dim_product.sql", "20_fact_sales.sql", "30_views.sql"]


def _d(ds: str) -> date:
    return date.fromisoformat(ds)


def _dir(ds: str, stage: str):
    p = config.DATA_DIR / ds / stage
    p.mkdir(parents=True, exist_ok=True)
    return p


def extract(ds: str) -> str:
    """Simulates the nightly ERP export: one CSV per table in the landing zone."""
    out = _dir(ds, "extract")
    for name, df in generate_daily(_d(ds)).items():
        df.to_csv(out / f"{name}.csv", index=False)
    log.info("Extract written to %s", out)
    return str(out)


def validate_step(ds: str) -> dict:
    src = _dir(ds, "extract")
    frames = {name: pd.read_csv(src / f"{name}.csv") for name in TABLES}
    clean, rejected, metrics = validate(frames, _d(ds))

    out = _dir(ds, "clean")
    for name, df in clean.items():
        df.to_csv(out / f"{name}.csv", index=False)
    rejected.to_csv(out / "dq_rejected_rows.csv", index=False)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    log.info("Validation metrics: %s", metrics)

    if metrics["reject_rate"] > config.MAX_REJECT_RATE:
        raise ValueError(f"Reject rate {metrics['reject_rate']:.1%} exceeds limit {config.MAX_REJECT_RATE:.1%}")
    return metrics


def _typed(name: str, df: pd.DataFrame) -> pd.DataFrame:
    for col in ("order_date", "rate_date", "_load_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col]).dt.date
    return df


def load_step(ds: str) -> dict:
    src = _dir(ds, "clean")
    c = bq.client()
    bq.ensure_datasets(c)
    loaded = {}
    for name in TABLES + ["dq_rejected_rows"]:
        df = _typed(name, pd.read_csv(src / f"{name}.csv"))
        loaded[name] = bq.load_table(c, name, df, _d(ds))
    log.info("Loaded rows: %s", loaded)
    return loaded


def transform_step(ds: str) -> None:
    c = bq.client()
    for sql_file in SQL_STEPS:
        log.info("Running %s", sql_file)
        bq.run_sql_file(c, sql_file, _d(ds))


def dq_step(ds: str) -> dict:
    results = run_checks(bq.client(), _d(ds))
    log.info("DQ checks passed: %s", results)
    return results


def run_all(ds: str, dry_run: bool = False) -> None:
    extract(ds)
    metrics = validate_step(ds)
    print(json.dumps(metrics, indent=2))
    if dry_run:
        print("Dry run: skipped BigQuery steps.")
        return
    load_step(ds)
    transform_step(ds)
    dq_step(ds)
