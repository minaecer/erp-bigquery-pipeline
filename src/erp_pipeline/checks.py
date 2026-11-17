"""Post-load data quality checks on the warehouse. Any failed check fails the Airflow task."""
from __future__ import annotations

from datetime import date

from . import bq

F = "`${PROJECT}.${DWH}.fact_sales`"

CHECKS = [
    ("fact_has_rows", f"SELECT COUNT(*) FROM {F} WHERE order_date = @ds", lambda v: v > 0),
    ("no_null_keys", f"SELECT COUNTIF(customer_id IS NULL OR product_id IS NULL) FROM {F} WHERE order_date = @ds",
     lambda v: v == 0),
    ("unique_grain_order_line",
     f"SELECT COUNT(*) FROM (SELECT order_id, line_no FROM {F} WHERE order_date = @ds GROUP BY 1, 2 HAVING COUNT(*) > 1)",
     lambda v: v == 0),
    ("no_orphan_products",
     f"SELECT COUNT(*) FROM {F} f LEFT JOIN `${{PROJECT}}.${{DWH}}.dim_product` p ON p.product_id = f.product_id "
     "WHERE f.order_date = @ds AND p.product_id IS NULL", lambda v: v == 0),
    ("no_orphan_customers",
     f"SELECT COUNT(*) FROM {F} f LEFT JOIN `${{PROJECT}}.${{DWH}}.dim_customer` c ON c.customer_id = f.customer_id "
     "WHERE f.order_date = @ds AND c.customer_id IS NULL", lambda v: v == 0),
    ("fx_applied_to_all_rows", f"SELECT COUNTIF(net_amount_try IS NULL) FROM {F} WHERE order_date = @ds",
     lambda v: v == 0),
    ("no_negative_amounts", f"SELECT COUNTIF(net_amount < 0) FROM {F} WHERE order_date = @ds", lambda v: v == 0),
]


class DataQualityError(Exception):
    pass


def run_checks(c, ds: date) -> dict[str, int]:
    results, failed = {}, []
    for name, sql, ok in CHECKS:
        value = int(bq.scalar(c, sql, ds))
        results[name] = value
        if not ok(value):
            failed.append(f"{name}={value}")
    if failed:
        raise DataQualityError(f"Data quality checks failed for {ds}: {', '.join(failed)}")
    return results
