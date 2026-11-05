"""Rank homes priced just above AED 2M by the rent they could earn.

Rent is estimated for each sale from the closest evidence available: the same project, then projects at a similar
price in the same area, then the area's rent adjusted for price. Ranking uses gross yield, before service charges,
vacancy and fees, none of which are in the data. Off-plan homes earn nothing until handover, so they are never ranked
with ready homes. These are homes priced at the threshold; the data does not show who received a visa.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from pipeline.clean_rents import DATA_CUT, clean
from pipeline.value_at_line import MARKET_PROCEDURES

PRICE_BAND = (2_000_000, 2_200_000)
TIER_BAND = (1_800_000, 2_400_000)
SALES_FROM = "2025-01-01"
RENTS_NOW = ("2025-11-04", DATA_CUT)
RENTS_LAST_YEAR = ("2024-11-04", "2025-11-03")
SIZE_TOLERANCE = 0.15
MIN_PROJECT_CONTRACTS = 20
MIN_POOL_CONTRACTS = 30
MIN_TIER_PROJECTS = 3
MIN_OPTION_SALES = 30
MIN_PROJECT_SHARE = 0.5
BOOTSTRAPS = 300
KEY = ["area_id", "rooms", "type"]


def load_sales(raw: str, cut: str = DATA_CUT) -> pd.DataFrame:
    return duckdb.connect().execute(f"""
        SELECT instance_date AS date, try_cast(actual_worth AS DOUBLE) AS value, try_cast(procedure_area AS DOUBLE) AS size,
               area_id, area_name_en AS area, nullif(trim(project_number), '') AS project, rooms_en AS rooms,
               CASE property_type_en WHEN 'Unit' THEN 'Flat' ELSE 'Villa' END AS type,
               CASE WHEN reg_type_en ILIKE '%off%' THEN 'off_plan' ELSE 'ready' END AS stage,
               try_cast(no_of_parties_role_2 AS INT) AS buyers
        FROM read_csv('{raw}', header=true, all_varchar=true, delim=',', quote='"', escape='"', union_by_name=true)
        WHERE trans_group_en = 'Sales' AND property_usage_en = 'Residential' AND property_type_en IN ('Unit', 'Villa')
          AND procedure_name_en IN {MARKET_PROCEDURES} AND instance_date >= '{SALES_FROM}' AND instance_date <= '{cut}'
          AND coalesce(nullif(trim(building_name_en), ''), nullif(trim(project_name_en), '')) IS NOT NULL
          AND rooms_en IS NOT NULL AND try_cast(procedure_area AS DOUBLE) > 0
          AND try_cast(actual_worth AS DOUBLE) / try_cast(procedure_area AS DOUBLE) BETWEEN 500 AND 200000
    """).df()


def fit_beta(rents: pd.DataFrame, sales: pd.DataFrame) -> float:
    """How far rent moves with price between projects in the same area and bedrooms."""
    r = rents.groupby([*KEY, "project"])["rent"].agg(["median", "size"])
    s = sales.groupby([*KEY, "project"])["value"].agg(["median", "size"])
    d = r[r["size"] >= MIN_PROJECT_CONTRACTS].add_suffix("_rent").join(s[s["size"] >= 5].add_suffix("_sale"), how="inner")
    d = np.log(d[["median_rent", "median_sale"]])
    d = d[d.groupby(KEY)["median_rent"].transform("size") >= 2]
    dev = d - d.groupby(KEY).transform("mean")
    return float((dev["median_rent"] * dev["median_sale"]).sum() / (dev["median_sale"] ** 2).sum())


def _near_size(contracts: pd.DataFrame, size: float) -> pd.DataFrame:
    return contracts[contracts["size"].between(size * (1 - SIZE_TOLERANCE), size * (1 + SIZE_TOLERANCE))]


def fallback_rent(pool: pd.DataFrame, cell_sales: pd.DataFrame, price: float, size: float, beta: float) -> tuple[float, str]:
    """Rent from the wider area when the project itself has too little evidence."""
    near = _near_size(pool, size)
    project_price = cell_sales.groupby("project")["value"].median()
    tier = near[near["project"].isin(project_price[project_price.between(*TIER_BAND)].index)]
    if len(tier) >= MIN_POOL_CONTRACTS and tier["project"].nunique() >= MIN_TIER_PROJECTS:
        return float(tier["rent"].median()), "price_tier"
    if len(near) >= MIN_POOL_CONTRACTS and len(cell_sales):
        return float(near["rent"].median() * (price / cell_sales["value"].median()) ** beta), "area_adjusted"
    return float("nan"), "none"


def estimate_rents(near: pd.DataFrame, rents: pd.DataFrame, sales: pd.DataFrame, beta: float) -> pd.DataFrame:
    """Add an estimated rent and its evidence level to each near-line sale."""
    rent_cells = dict(tuple(rents.groupby(KEY)))
    sale_cells = dict(tuple(sales.groupby(KEY)))
    empty = rents.iloc[0:0]
    parts = []
    for key, cell in near.groupby(KEY):
        pool, cell_sales = rent_cells.get(key, empty), sale_cells.get(key, sales.iloc[0:0])
        wide = fallback_rent(pool, cell_sales, cell["value"].median(), cell["size"].median(), beta)
        for project, group in cell.groupby("project", dropna=False):
            own = _near_size(pool[pool["project"] == project], group["size"].median()) if pd.notna(project) else empty
            rent, level = (float(own["rent"].median()), "project") if len(own) >= MIN_PROJECT_CONTRACTS else wide
            parts.append(group.assign(rent=rent, level=level))
    return pd.concat(parts, ignore_index=True)


def _interval(frame: pd.DataFrame, rng: np.random.Generator) -> tuple[float, float]:
    rent, value = frame["rent"].to_numpy(), frame["value"].to_numpy()
    picks = rng.integers(0, len(frame), (BOOTSTRAPS, len(frame)))
    yields = np.median(rent[picks], axis=1) / np.median(value[picks], axis=1) * 100
    return round(float(np.percentile(yields, 2.5)), 2), round(float(np.percentile(yields, 97.5)), 2)


def options(estimated: pd.DataFrame, rents: pd.DataFrame, sales: pd.DataFrame, seed: int = 7) -> pd.DataFrame:
    """One row for each area, bedroom count, type and stage with enough sales."""
    rng = np.random.default_rng(seed)
    all_rent = rents.groupby(KEY)["rent"].median()
    all_price = sales.groupby(KEY)["value"].median()
    rows = []
    for (stage, *key), group in estimated.groupby(["stage", *KEY]):
        known = group[group["level"] != "none"]
        if len(group) < MIN_OPTION_SALES or len(known) < MIN_OPTION_SALES:
            continue
        rent, price = known["rent"].median(), known["value"].median()
        low, high = _interval(known, rng)
        k = tuple(key)
        rows.append({"stage": stage, "area": group["area"].iloc[0], "area_id": k[0], "rooms": k[1], "type": k[2], "sales": len(group),
                     "price_aed": round(price), "size_sqm": round(float(group["size"].median()), 1), "rent_aed": round(rent),
                     "yield_pct": round(rent / price * 100, 2), "low_pct": low, "high_pct": high,
                     "project_share": round(float((group["level"] == "project").mean()), 2),
                     "tier_share": round(float((group["level"] == "price_tier").mean()), 2),
                     "area_share": round(float((group["level"] == "area_adjusted").mean()), 2),
                     "all_price_yield_pct": round(all_rent[k] / all_price[k] * 100, 2) if k in all_rent.index and k in all_price.index else None})
    return pd.DataFrame(rows)


def rank_ready(table: pd.DataFrame, margin: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rank only ready flats on mostly project evidence. Options within the estimate's typical error of the leader share the top tier."""
    ready = table[(table["stage"] == "ready") & (table["type"] == "Flat")].sort_values("yield_pct", ascending=False)
    ranked = ready[ready["project_share"] >= MIN_PROJECT_SHARE].copy()
    if len(ranked):
        ranked["top_tier"] = ranked["yield_pct"] >= ranked["yield_pct"].iloc[0] - margin
    return ranked, ready[ready["project_share"] < MIN_PROJECT_SHARE]


def leave_project_out(near: pd.DataFrame, rents: pd.DataFrame, sales: pd.DataFrame, beta: float) -> dict:
    """How wrong is the wider-area estimate for a project whose real rent we know?"""
    rows = []
    ready = near[(near["stage"] == "ready") & (near["type"] == "Flat") & near["project"].notna()]
    for (*key, project), group in ready.groupby([*KEY, "project"]):
        k = tuple(key)
        pool = rents[(rents["area_id"] == k[0]) & (rents["rooms"] == k[1]) & (rents["type"] == k[2])]
        own = _near_size(pool[pool["project"] == project], group["size"].median())
        if len(own) < MIN_PROJECT_CONTRACTS:
            continue
        cell = sales[(sales["area_id"] == k[0]) & (sales["rooms"] == k[1]) & (sales["type"] == k[2]) & (sales["project"] != project)]
        rent, level = fallback_rent(pool[pool["project"] != project], cell, group["value"].median(), group["size"].median(), beta)
        if level != "none":
            rows.append({"error": rent / own["rent"].median() - 1, "points": (rent - own["rent"].median()) / group["value"].median() * 100})
    d = pd.DataFrame(rows)
    if d.empty:
        return {"projects": 0}
    return {"projects": len(d), "median_abs_error_pct": round(float(d["error"].abs().median() * 100), 1),
            "p90_abs_error_pct": round(float(d["error"].abs().quantile(0.9) * 100), 1),
            "median_bias_pct": round(float(d["error"].median() * 100), 1),
            "median_abs_yield_points": round(float(d["points"].abs().median()), 2),
            "p90_abs_yield_points": round(float(d["points"].abs().quantile(0.9)), 2)}


def new_build_premium(all_rents: pd.DataFrame, now: pd.DataFrame) -> dict:
    """Projects first let from 2025 against the area's rents, because off-plan homes will be new when let."""
    first = all_rents.groupby("project")["start"].min()
    new = first[first >= "2025-01-01"].index
    area = now.groupby(KEY)["rent"].median().rename("area_rent")
    cells = now[now["project"].isin(new)].groupby([*KEY, "project"])["rent"].agg(["median", "size"])
    cells = cells[cells["size"] >= MIN_PROJECT_CONTRACTS].join(area, on=KEY)
    ratio = cells["median"] / cells["area_rent"]
    return {"cells": len(ratio), "median_ratio": round(float(ratio.median()), 3) if len(ratio) else None}


def compare(base: pd.DataFrame, other: pd.DataFrame) -> dict:
    """How much an option's yield and rank change under another assumption."""
    key = ["stage", "area_id", "rooms", "type"]
    d = base.merge(other, on=key, suffixes=("", "_other"))
    if d.empty:
        return {"options": 0}
    return {"options": len(d), "median_abs_points": round(float((d["yield_pct"] - d["yield_pct_other"]).abs().median()), 2),
            "spearman": round(float(d["yield_pct"].corr(d["yield_pct_other"], method="spearman")), 2)}


def _records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.drop(columns=["area_id"]).to_json(orient="records"))


def run(rents_raw: str, sales_raw: str) -> dict:
    all_rents, funnel = clean(rents_raw)
    sales = load_sales(sales_raw)
    now = all_rents[all_rents["start"].between(*RENTS_NOW)]
    last_year = all_rents[all_rents["start"].between(*RENTS_LAST_YEAR)]
    near = sales[sales["value"].between(*PRICE_BAND)]
    beta = fit_beta(now, sales)
    estimated = estimate_rents(near, now, sales, beta)
    table = options(estimated, now, sales)
    held_out = leave_project_out(near, now, sales, beta)
    ranked, thin = rank_ready(table, held_out["median_abs_yield_points"])
    levels = estimated.groupby(["stage", "type", "level"]).size().reset_index(name="sales")
    return {
        "funnel": funnel, "beta": round(beta, 2), "near_line_sales": len(near), "evidence": levels.to_dict(orient="records"),
        "ready_ranked": _records(ranked), "ready_indicative": _records(thin),
        "off_plan_indicative": _records(table[(table["stage"] == "off_plan") & (table["type"] == "Flat")].sort_values("yield_pct", ascending=False)),
        "villas_not_ranked": _records(table[table["type"] == "Villa"]),
        "checks": {
            "leave_project_out": held_out,
            "new_build_premium": new_build_premium(all_rents, now),
            "last_year_rents": compare(table, options(estimate_rents(near, last_year, sales, beta), last_year, sales)),
            "person_tenants_only": compare(table, options(estimate_rents(near, now[now["tenant"] == "Person"], sales, beta), now[now["tenant"] == "Person"], sales)),
            "single_buyer_sales": compare(table, options(estimated[estimated["buyers"] == 1], now, sales)),
        },
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rents", default="data/raw/rents/*.csv.gz")
    p.add_argument("--sales", default="data/raw/transactions/*.csv.gz")
    p.add_argument("--out", default="validation/rent_yields.json", type=Path)
    a = p.parse_args()
    a.out.write_text(json.dumps(run(a.rents, a.sales), indent=1) + "\n")
    print(f"wrote {a.out}")
