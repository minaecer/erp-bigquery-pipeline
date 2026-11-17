from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "sql"
DATA_DIR = Path(os.environ.get("DATA_DIR", ROOT / "data"))

BQ_LOCATION = os.environ.get("BQ_LOCATION", "EU")
STG_DATASET = os.environ.get("BQ_STG_DATASET", "erp_stg")
DWH_DATASET = os.environ.get("BQ_DWH_DATASET", "erp_dwh")

# Fail the run if more than this share of extracted rows is rejected by validation.
MAX_REJECT_RATE = float(os.environ.get("MAX_REJECT_RATE", "0.05"))
# Staging partitions are dropped after this many days to keep storage cost low.
STG_PARTITION_EXPIRATION_DAYS = int(os.environ.get("STG_PARTITION_EXPIRATION_DAYS", "60"))


def project_id() -> str:
    pid = os.environ.get("GCP_PROJECT_ID")
    if not pid:
        raise RuntimeError("Set GCP_PROJECT_ID (see .env.example).")
    return pid
