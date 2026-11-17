"""Row-level validation. Bad rows are not silently dropped: each one is recorded with a reason."""
from __future__ import annotations

from datetime import date

import pandas as pd

REJECT_COLUMNS = ["table_name", "record_key", "reason"]


def validate(frames: dict[str, pd.DataFrame], ds: date):
    rejected: list[pd.DataFrame] = []

    def take(df: pd.DataFrame, mask: pd.Series, table: str, reason: str) -> pd.DataFrame:
        bad = df[mask]
        if len(bad):
            rejected.append(
                pd.DataFrame({"table_name": table, "record_key": bad["_key"].astype(str).to_numpy(), "reason": reason})
            )
        return df[~mask]

    customers = frames["customers"].drop_duplicates("customer_id").copy()
    products = frames["products"].drop_duplicates("product_id").copy()
    orders = frames["sales_orders"].copy()
    lines = frames["sales_lines"].copy()
    rows_in = len(orders) + len(lines)

    # --- orders ---
    orders["_key"] = orders["order_id"].astype(str)
    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
    orders = take(orders, orders["customer_id"].isna(), "sales_orders", "missing_customer_id")
    orders = take(orders, orders["order_date"].isna(), "sales_orders", "invalid_order_date")
    orders = take(orders, orders.duplicated("order_id"), "sales_orders", "duplicate_order")
    orders = take(orders, ~orders["customer_id"].isin(customers["customer_id"]), "sales_orders", "unknown_customer")

    # --- lines ---
    lines["_key"] = lines["order_id"].astype(str) + "#" + lines["line_no"].astype(str)
    lines = take(lines, lines.duplicated(["order_id", "line_no"]), "sales_lines", "duplicate_line")
    lines = take(lines, lines["quantity"] <= 0, "sales_lines", "non_positive_quantity")
    lines = take(lines, lines["unit_price"] <= 0, "sales_lines", "non_positive_price")
    lines = take(lines, ~lines["product_id"].isin(products["product_id"]), "sales_lines", "unknown_product")
    lines = take(lines, ~lines["order_id"].isin(orders["order_id"]), "sales_lines", "orphan_line")

    fx = frames["fx_rates"].copy()
    fx["rate_date"] = pd.to_datetime(fx["rate_date"])

    clean = {
        "customers": customers,
        "products": products,
        "sales_orders": orders.drop(columns="_key"),
        "sales_lines": lines.drop(columns="_key"),
        "fx_rates": fx,
    }
    for name in ("sales_orders", "sales_lines", "fx_rates"):
        for col in clean[name].columns:
            if pd.api.types.is_datetime64_any_dtype(clean[name][col]):
                clean[name][col] = clean[name][col].dt.date
    for df in clean.values():
        df["_load_date"] = ds

    rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame(columns=REJECT_COLUMNS)
    rejected_df["_load_date"] = ds

    metrics = {
        "rows_in": int(rows_in),
        "orders_clean": int(len(orders)),
        "lines_clean": int(len(lines)),
        "rejected": int(len(rejected_df)),
        "reject_rate": round(len(rejected_df) / rows_in, 4) if rows_in else 0.0,
        "reasons": {k: int(v) for k, v in rejected_df["reason"].value_counts().items()},
    }
    return clean, rejected_df, metrics
