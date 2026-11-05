"""Export CSVs for Looker Studio upload, and a manifest of totals to check the live report against.

Only the two files needed to test the public link for now. Figures needing 5-minute detail are
uploaded as finished values from golden_values.json, because Looker cannot recalculate them.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

MAX_UPLOAD_MB = 100  # Looker Studio's limit per data set
INSIGHT_TABLES = ["cost_concentration", "cap_value", "load_shift", "battery_upper_bound", "price_regimes"]


def _fy_label(fy: pd.Series) -> pd.Series:
    """Text, so Looker does not sum the year or show it as 2,026."""
    return "FY" + fy.astype(str)


def insights_region_fy(golden: dict, regions: pd.DataFrame) -> pd.DataFrame:
    """One row per region and complete financial year, keeping only years with every insight."""
    first, *rest = (pd.DataFrame(golden[t]) for t in INSIGHT_TABLES)
    out = regions[["region_code", "region_name", "sort_order"]].merge(first, on="region_code", validate="one_to_many")
    for rows in rest:
        out = out.merge(rows, on=["region_code", "fy"], validate="one_to_one")
    out = out.sort_values(["sort_order", "fy"]).reset_index(drop=True)
    return out.assign(financial_year=_fy_label(out["fy"])).drop(columns="fy")


def forecast_halfhour(forecast: pd.DataFrame, regions: pd.DataFrame) -> pd.DataFrame:
    """Half-hourly forecast rounded to 0.1 MW. Timestamps are market time (UTC+10), as text Looker can parse."""
    out = forecast.merge(regions[["region_code", "region_name"]], on="region_code", validate="many_to_one")
    values = ["demand_mw", "seasonal_naive", "no_weather", "with_weather", "p10", "p90"]
    out[values] = out[values].round(1)
    out["interval_start"] = out["interval_start"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return out.assign(financial_year=_fy_label(out["fy"]))[
        ["region_name", "interval_start", "financial_year", *values]
    ].sort_values(["region_name", "interval_start"]).reset_index(drop=True)


def write_csv(df: pd.DataFrame, path: Path) -> dict:
    df.to_csv(path, index=False)
    mb = path.stat().st_size / 1e6
    if mb > MAX_UPLOAD_MB:
        raise ValueError(f"{path.name} is {mb:.1f} MB, over the {MAX_UPLOAD_MB} MB upload limit")
    return {"file": path.name, "rows": len(df), "mb": round(mb, 1)}


def checks(insights: pd.DataFrame, fc: pd.DataFrame, latest: str) -> dict:
    """Figures to compare by eye with the live report."""
    i = insights[insights["financial_year"] == latest].set_index("region_code")
    f = fc[fc["financial_year"] == latest].groupby("region_name")
    return {
        "financial_year": latest,
        "load_shift_saving_aud_per_mw_year": i["saving_aud_per_mw_year"].round(0).to_dict(),
        "forecast_rows": f.size().to_dict(),
        "forecast_average_demand_mw": f["demand_mw"].mean().round(1).to_dict(),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--star", default="data/star", type=Path)
    p.add_argument("--golden", default="validation/golden_values.json", type=Path)
    p.add_argument("--out", default="looker", type=Path)
    p.add_argument("--manifest", default="validation/looker_manifest.json", type=Path)
    a = p.parse_args()
    a.out.mkdir(exist_ok=True)
    regions = pd.read_parquet(a.star / "dim_region.parquet")
    insights = insights_region_fy(json.loads(a.golden.read_text()), regions)
    fc = forecast_halfhour(pd.read_parquet(a.star / "fact_forecast.parquet"), regions)
    files = [write_csv(insights, a.out / "insights_region_fy.csv"), write_csv(fc, a.out / "forecast_halfhour.csv")]
    a.manifest.write_text(json.dumps({"files": files, "checks": checks(insights, fc, insights["financial_year"].max())}, indent=1))
    print(files)
