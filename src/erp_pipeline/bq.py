"""Thin BigQuery helpers. google-cloud-bigquery is imported lazily so --dry-run works without it."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from . import config


def _bq():
    from google.cloud import bigquery

    return bigquery


def client():
    return _bq().Client(project=config.project_id(), location=config.BQ_LOCATION)


def schemas():
    bq = _bq()
    F = bq.SchemaField
    return {
        "customers": [F("customer_id", "STRING"), F("customer_name", "STRING"), F("segment", "STRING"),
                      F("city", "STRING"), F("region", "STRING"), F("_load_date", "DATE")],
        "products": [F("product_id", "STRING"), F("product_name", "STRING"), F("category", "STRING"),
                     F("list_price_eur", "FLOAT64"), F("_load_date", "DATE")],
        "sales_orders": [F("order_id", "STRING"), F("order_date", "DATE"), F("customer_id", "STRING"),
                         F("region", "STRING"), F("currency", "STRING"), F("status", "STRING"),
                         F("_load_date", "DATE")],
        "sales_lines": [F("order_id", "STRING"), F("line_no", "INT64"), F("product_id", "STRING"),
                        F("quantity", "INT64"), F("unit_price", "FLOAT64"), F("discount_pct", "INT64"),
                        F("_load_date", "DATE")],
        "fx_rates": [F("rate_date", "DATE"), F("currency", "STRING"), F("rate_to_try", "FLOAT64"),
                     F("_load_date", "DATE")],
        "dq_rejected_rows": [F("table_name", "STRING"), F("record_key", "STRING"), F("reason", "STRING"),
                             F("_load_date", "DATE")],
    }


def ensure_datasets(c) -> None:
    bq = _bq()
    for name in (config.STG_DATASET, config.DWH_DATASET):
        ds = bq.Dataset(f"{config.project_id()}.{name}")
        ds.location = config.BQ_LOCATION
        c.create_dataset(ds, exists_ok=True)


def load_table(c, name: str, df: pd.DataFrame, ds: date) -> int:
    """Idempotent load: delete today's partition, then append. Re-running a day never duplicates rows."""
    bq = _bq()
    schema = schemas()[name]
    table_id = f"{config.project_id()}.{config.STG_DATASET}.{name}"

    table = bq.Table(table_id, schema=schema)
    table.time_partitioning = bq.TimePartitioning(
        type_=bq.TimePartitioningType.DAY,
        field="_load_date",
        expiration_ms=config.STG_PARTITION_EXPIRATION_DAYS * 24 * 3600 * 1000,
    )
    c.create_table(table, exists_ok=True)

    c.query(
        f"DELETE FROM `{table_id}` WHERE _load_date = @ds",
        job_config=bq.QueryJobConfig(query_parameters=[bq.ScalarQueryParameter("ds", "DATE", ds)]),
    ).result()

    if df.empty:
        return 0
    df = df[[f.name for f in schema]]
    job = c.load_table_from_dataframe(
        df, table_id, job_config=bq.LoadJobConfig(schema=schema, write_disposition="WRITE_APPEND")
    )
    job.result()
    return len(df)


def _render(sql: str) -> str:
    return (
        sql.replace("${PROJECT}", config.project_id())
        .replace("${STG}", config.STG_DATASET)
        .replace("${DWH}", config.DWH_DATASET)
    )


def run_sql_file(c, filename: str, ds: date) -> None:
    bq = _bq()
    sql = _render(Path(config.SQL_DIR, filename).read_text())
    c.query(sql, job_config=bq.QueryJobConfig(query_parameters=[bq.ScalarQueryParameter("ds", "DATE", ds)])).result()


def scalar(c, sql: str, ds: date):
    bq = _bq()
    rows = list(
        c.query(_render(sql), job_config=bq.QueryJobConfig(query_parameters=[bq.ScalarQueryParameter("ds", "DATE", ds)])).result()
    )
    return rows[0][0]
