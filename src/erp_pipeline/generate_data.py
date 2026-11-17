"""Synthetic ERP (SAP/Uyumsoft-style) sales extract.

Master data (customers, products) is fixed by a seed. Transactions are generated per
day, deterministically from the date, and deliberately contain ~1% dirty records
(duplicates, missing keys, negative quantities, unknown products, bad dates) so the
validation layer has real work to do. No real company data is used.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd

REGIONS = {
    "Marmara": ["Istanbul", "Bursa", "Kocaeli"],
    "Aegean": ["Izmir", "Mugla", "Aydin"],
    "Mediterranean": ["Antalya", "Mersin", "Adana"],
    "Central Anatolia": ["Ankara", "Konya", "Kayseri"],
}
SEGMENTS = ["Distributor", "Contractor", "Retail", "Architect"]
CATEGORIES = ["Slab", "Cut-to-size", "Sink", "Accessory"]
MASTER_SEED = 42
N_CUSTOMERS = 300
N_PRODUCTS = 80


def _master() -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(MASTER_SEED)
    cities = [(c, r) for r, cs in REGIONS.items() for c in cs]
    idx = rng.integers(0, len(cities), N_CUSTOMERS)
    customers = pd.DataFrame(
        {
            "customer_id": [f"C{i:04d}" for i in range(1, N_CUSTOMERS + 1)],
            "customer_name": [f"Customer {i:04d} Ltd." for i in range(1, N_CUSTOMERS + 1)],
            "segment": rng.choice(SEGMENTS, N_CUSTOMERS),
            "city": [cities[i][0] for i in idx],
            "region": [cities[i][1] for i in idx],
        }
    )
    products = pd.DataFrame(
        {
            "product_id": [f"P{i:03d}" for i in range(1, N_PRODUCTS + 1)],
            "product_name": [f"Product {i:03d}" for i in range(1, N_PRODUCTS + 1)],
            "category": rng.choice(CATEGORIES, N_PRODUCTS),
            "list_price_eur": np.round(rng.lognormal(4.2, 0.6, N_PRODUCTS), 2),
        }
    )
    return customers, products


def _eur_try_rate(ds: date) -> float:
    days = (ds - date(2026, 1, 1)).days
    noise = np.random.default_rng(ds.toordinal() + 1).normal(0, 0.15)
    return round(float(45 + 0.02 * days + noise), 4)


def _inject_dirty(orders: pd.DataFrame, lines: pd.DataFrame, rng: np.random.Generator):
    orders, lines = orders.copy(), lines.copy()
    k = max(1, int(len(lines) * 0.01))

    neg = rng.choice(len(lines), k, replace=False)
    lines.loc[neg, "quantity"] = -lines.loc[neg, "quantity"]
    unknown = rng.choice(len(lines), k, replace=False)
    lines.loc[unknown, "product_id"] = "P999"
    dup_lines = lines.iloc[rng.choice(len(lines), k, replace=False)]
    lines = pd.concat([lines, dup_lines], ignore_index=True)

    ko = max(1, int(len(orders) * 0.01))
    no_cust = rng.choice(len(orders), ko, replace=False)
    orders.loc[no_cust, "customer_id"] = None
    bad_date = rng.choice(len(orders), ko, replace=False)
    orders.loc[bad_date, "order_date"] = "not-a-date"
    orders = pd.concat([orders, orders.iloc[rng.choice(len(orders), ko, replace=False)]], ignore_index=True)
    return orders, lines


def generate_daily(ds: date) -> dict[str, pd.DataFrame]:
    """Return the ERP extract for one business day as raw (unvalidated) tables."""
    rng = np.random.default_rng(ds.toordinal())
    customers, products = _master()

    n_orders = int(rng.integers(150, 350))
    if ds.weekday() >= 5:
        n_orders //= 3

    cust_idx = rng.integers(0, len(customers), n_orders)
    orders = pd.DataFrame(
        {
            "order_id": [f"SO{ds:%Y%m%d}{i:04d}" for i in range(1, n_orders + 1)],
            "order_date": ds.isoformat(),
            "customer_id": customers["customer_id"].to_numpy()[cust_idx],
            "region": customers["region"].to_numpy()[cust_idx],
            "currency": rng.choice(["TRY", "EUR"], n_orders, p=[0.75, 0.25]),
            "status": rng.choice(["Invoiced", "Shipped", "Cancelled"], n_orders, p=[0.75, 0.20, 0.05]),
        }
    )

    fx = _eur_try_rate(ds)
    n_lines = rng.integers(1, 6, n_orders)
    lines = orders.loc[orders.index.repeat(n_lines), ["order_id", "currency"]].reset_index(drop=True)
    lines["line_no"] = lines.groupby("order_id").cumcount() + 1
    pidx = rng.integers(0, len(products), len(lines))
    base_eur = products["list_price_eur"].to_numpy()[pidx]
    currency_mult = np.where(lines["currency"] == "EUR", 1.0, fx)
    lines["product_id"] = products["product_id"].to_numpy()[pidx]
    lines["quantity"] = rng.integers(1, 41, len(lines))
    lines["unit_price"] = np.round(base_eur * currency_mult * rng.uniform(0.95, 1.05, len(lines)), 2)
    lines["discount_pct"] = rng.choice([0, 0, 5, 10, 15], len(lines))
    lines = lines.drop(columns="currency")

    orders, lines = _inject_dirty(orders, lines, rng)
    fx_rates = pd.DataFrame({"rate_date": [ds.isoformat()], "currency": ["EUR"], "rate_to_try": [fx]})

    return {
        "customers": customers,
        "products": products,
        "sales_orders": orders,
        "sales_lines": lines,
        "fx_rates": fx_rates,
    }
