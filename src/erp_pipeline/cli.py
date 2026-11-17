"""Run the whole pipeline without Airflow:  python -m erp_pipeline.cli --ds 2026-11-16 [--dry-run]"""
import argparse
import logging

from .pipeline import run_all

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--ds", required=True, help="Business date, YYYY-MM-DD")
    ap.add_argument("--dry-run", action="store_true", help="Generate + validate only; no BigQuery calls")
    args = ap.parse_args()
    run_all(args.ds, dry_run=args.dry_run)
