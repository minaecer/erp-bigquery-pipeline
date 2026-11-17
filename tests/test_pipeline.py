from datetime import date

from erp_pipeline.generate_data import generate_daily
from erp_pipeline.transform import validate

DS = date(2026, 11, 16)  # a Monday


def _run():
    frames = generate_daily(DS)
    return frames, *validate(frames, DS)


def test_generation_is_deterministic():
    a, b = generate_daily(DS), generate_daily(DS)
    assert a["sales_lines"].equals(b["sales_lines"])


def test_dirty_data_is_injected_and_rejected():
    _, clean, rejected, metrics = _run()
    assert metrics["rejected"] > 0
    expected = {"duplicate_line", "non_positive_quantity", "unknown_product", "missing_customer_id"}
    assert expected <= set(rejected["reason"])


def test_clean_lines_respect_rules():
    frames, clean, _, _ = _run()
    lines, orders = clean["sales_lines"], clean["sales_orders"]
    assert not lines.duplicated(["order_id", "line_no"]).any()
    assert (lines["quantity"] > 0).all() and (lines["unit_price"] > 0).all()
    assert lines["product_id"].isin(frames["products"]["product_id"]).all()
    assert lines["order_id"].isin(orders["order_id"]).all()
    assert orders["customer_id"].notna().all() and not orders.duplicated("order_id").any()


def test_nothing_is_lost_silently():
    frames, clean, rejected, metrics = _run()
    rows_in = len(frames["sales_orders"]) + len(frames["sales_lines"])
    assert rows_in == metrics["orders_clean"] + metrics["lines_clean"] + metrics["rejected"]


def test_reject_rate_is_below_threshold():
    *_, metrics = _run()
    assert metrics["reject_rate"] < 0.05
