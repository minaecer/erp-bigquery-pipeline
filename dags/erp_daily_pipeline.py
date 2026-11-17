from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.models.baseoperator import chain
from airflow.operators.python import PythonOperator

from erp_pipeline import pipeline

default_args = {
    "owner": "data-engineering",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

STEPS = [
    ("extract_erp_data", pipeline.extract),
    ("validate_and_clean", pipeline.validate_step),
    ("load_to_bigquery_staging", pipeline.load_step),
    ("build_star_schema", pipeline.transform_step),
    ("data_quality_checks", pipeline.dq_step),
]

with DAG(
    dag_id="erp_daily_sales_pipeline",
    description="Synthetic ERP sales -> BigQuery staging -> star schema -> DQ checks",
    start_date=datetime(2026, 11, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["erp", "bigquery", "etl"],
) as dag:
    tasks = [
        PythonOperator(task_id=task_id, python_callable=fn, op_kwargs={"ds": "{{ ds }}"})
        for task_id, fn in STEPS
    ]
    chain(*tasks)
