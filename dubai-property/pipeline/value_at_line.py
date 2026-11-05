"""Do buyers get less home just above a round price than just below it?

Each sale gets an expected value from sales in the same building and year, given its size. Sales within 10% of the
line are left out of that estimate, so they cannot influence it. The gap is the actual price minus the expected value.
A step up in the gap at the line means similar money buys a smaller or lesser home just above it. Other round prices
and earlier years show how much of that step comes from round numbers alone.
"""
import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

LINES = [1_500_000, 2_000_000, 2_500_000, 3_000_000, 4_000_000]
TARGET = 2_000_000
NEARBY = [1_700_000, 1_800_000, 1_900_000, 2_100_000, 2_200_000, 2_300_000]
WINDOW = 0.10
MIN_FIT_SALES = 5
BOOTSTRAPS = 300
PERIODS = {"before_2022": ("2015-01-01", "2022-01-01"), "from_q2_2022": ("2022-04-01", "2027-01-01")}
MARKET_PROCEDURES = ("Sell", "Sell - Pre registration", "Delayed Sell", "Sale On Payment Plan")


def load(raw: str) -> pd.DataFrame:
    return duckdb.connect().execute(f"""
        SELECT instance_date AS date, substr(instance_date, 1, 4) AS year,
               try_cast(actual_worth AS DOUBLE) AS value, try_cast(procedure_area AS DOUBLE) AS size,
               CASE WHEN reg_type_en ILIKE '%off%' THEN 'off_plan' ELSE 'ready' END AS stage,
               area_name_en || '|' || coalesce(nullif(trim(building_name_en), ''), nullif(trim(project_name_en), '')) AS place
        FROM read_csv('{raw}', header=true, all_varchar=true, delim=',', quote='"', escape='"', union_by_name=true)
        WHERE trans_group_en = 'Sales' AND property_usage_en = 'Residential' AND property_type_en IN ('Unit', 'Villa')
          AND procedure_name_en IN {MARKET_PROCEDURES} AND instance_date >= '2015-01-01'
          AND coalesce(nullif(trim(building_name_en), ''), nullif(trim(project_name_en), '')) IS NOT NULL
          AND try_cast(procedure_area AS DOUBLE) > 0
          AND try_cast(actual_worth AS DOUBLE) / try_cast(procedure_area AS DOUBLE) BETWEEN 500 AND 200000
    """).df()


def value_gap(df: pd.DataFrame, line: float, window: float = WINDOW) -> pd.DataFrame:
    """Log gap between each near-line sale's price and its expected value, plus its distance from the line."""
    d = df.assign(group=df["place"] + "|" + df["year"] + "|" + df["stage"], log_value=np.log(df["value"]),
                  log_size=np.log(df["size"]))
    d["x"] = d["log_value"] - np.log(line)
    near = d["x"].abs() <= window
    fit = d[~near]
    fit = fit[fit.groupby("group")["log_value"].transform("size") >= MIN_FIT_SALES]
    g = fit.groupby("group")
    size_dev, value_dev = fit["log_size"] - g["log_size"].transform("mean"), fit["log_value"] - g["log_value"].transform("mean")
    slope = (size_dev * value_dev).sum() / (size_dev ** 2).sum()
    centre = g[["log_value", "log_size"]].mean().add_suffix("_centre")
    out = d[near].join(centre, on="group").dropna(subset=["log_value_centre"])
    out["gap"] = out["log_value"] - out["log_value_centre"] - slope * (out["log_size"] - out["log_size_centre"])
    return out


def _step(gap: np.ndarray, x: np.ndarray, weights: np.ndarray) -> float:
    above = (x > 0).astype(float)
    design = np.column_stack([np.ones_like(x), above, x, x * above])
    root = np.sqrt(weights)
    return float(np.linalg.lstsq(design * root[:, None], gap * root, rcond=None)[0][1])


def step_at_line(near: pd.DataFrame, line: float, seed: int = 42) -> dict:
    """Step in the gap at the line. Sales exactly on the line are measured apart, because they are a spike of round prices."""
    on_line = near["value"] == line
    off = near[~on_line]
    codes = pd.factorize(off["group"])[0]
    gap, x = off["gap"].to_numpy(), off["x"].to_numpy()
    step = _step(gap, x, np.ones(len(off)))
    rng = np.random.default_rng(seed)
    n_groups = codes.max() + 1
    draws = [_step(gap, x, np.bincount(rng.integers(0, n_groups, n_groups), minlength=n_groups)[codes].astype(float))
             for _ in range(BOOTSTRAPS)]
    low, high = np.quantile(draws, [0.025, 0.975])
    aed = lambda s: round(float(np.expm1(s)) * line)
    return {"line": line, "sales_near": len(off), "groups": int(n_groups), "sales_on_line": int(on_line.sum()),
            "step_pct": round(float(np.expm1(step)) * 100, 2), "low_pct": round(float(np.expm1(low)) * 100, 2),
            "high_pct": round(float(np.expm1(high)) * 100, 2), "step_aed": aed(step), "low_aed": aed(low), "high_aed": aed(high)}


def robustness(df: pd.DataFrame) -> list[dict]:
    """Checks on the main result: other window widths, nearby prices that are not the line, and each year alone."""
    start, end = PERIODS["from_q2_2022"]
    d = df[(df["date"] >= start) & (df["date"] < end)]
    rows = [{"check": f"window_{w}", **step_at_line(value_gap(d, TARGET, w), TARGET)} for w in (0.05, 0.075, 0.15)]
    rows += [{"check": "nearby_price", **step_at_line(value_gap(d, line), line)} for line in NEARBY]
    rows += [{"check": f"year_{y}", **step_at_line(value_gap(part, TARGET), TARGET)} for y, part in d.groupby("year")]
    return rows


def crowding(df: pd.DataFrame, band: float = 50_000) -> list[dict]:
    """Sales just above a price divided by sales just below it, in each period."""
    rows = []
    for period, (start, end) in PERIODS.items():
        d = df[(df["date"] >= start) & (df["date"] < end)]
        for line in sorted(LINES + NEARBY):
            above = int(((d["value"] >= line) & (d["value"] < line + band)).sum())
            below = int(((d["value"] >= line - band) & (d["value"] < line)).sum())
            rows.append({"period": period, "line": line, "below": below, "above": above, "ratio": round(above / below, 2) if below else None})
    return rows


def run(df: pd.DataFrame) -> list[dict]:
    rows = []
    for period, (start, end) in PERIODS.items():
        d = df[(df["date"] >= start) & (df["date"] < end)]
        for stage, part in [("all", d), ("ready", d[d["stage"] == "ready"]), ("off_plan", d[d["stage"] == "off_plan"])]:
            for line in LINES:
                rows.append({"period": period, "stage": stage, **step_at_line(value_gap(part, line), line)})
    return rows


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--raw", default="data/raw/transactions/*.csv.gz")
    p.add_argument("--out", default="validation/value_at_line.json", type=Path)
    a = p.parse_args()
    sales = load(a.raw)
    results = {"crowding": crowding(sales), "by_line": run(sales), "robustness": robustness(sales)}
    a.out.parent.mkdir(exist_ok=True)
    a.out.write_text(json.dumps(results, indent=1) + "\n")
    print(pd.DataFrame(results["crowding"]).to_string(index=False))
