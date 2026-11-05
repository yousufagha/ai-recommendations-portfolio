import json
from pathlib import Path

import duckdb
import pandas as pd
import pytest

from pipeline.export_looker import forecast_halfhour, insights_region_fy, write_csv

REGIONS = pd.DataFrame({"region_code": ["SA1", "VIC1"], "region_name": ["South Australia", "Victoria"], "sort_order": [3, 5]})


def golden():
    keys = {"cost_concentration": "top_1pct_cost_share", "cap_value": "cap_300_aud_mwh",
            "load_shift": "saving_aud_per_mw_year", "battery_upper_bound": "gross_aud_per_mw_year",
            "price_regimes": "negative_time_share"}
    g = {t: [{"region_code": r, "fy": 2026, k: 1.5} for r in ("SA1", "VIC1")] for t, k in keys.items()}
    g["price_regimes"] += [{"region_code": "SA1", "fy": 2021, "negative_time_share": 0.1},
                           {"region_code": "SA1", "fy": 2027, "negative_time_share": 0.2}]
    return g


def test_insights_keep_only_years_with_every_figure():
    out = insights_region_fy(golden(), REGIONS)
    assert sorted(out["financial_year"].unique()) == ["FY2026"]
    assert len(out) == 2
    assert {"top_1pct_cost_share", "cap_300_aud_mwh", "saving_aud_per_mw_year", "gross_aud_per_mw_year",
            "negative_time_share", "region_name"} <= set(out.columns)


def test_forecast_rounds_and_formats_timestamps():
    f = pd.DataFrame({"region_code": ["SA1"], "interval_start": pd.to_datetime(["2025-07-01 00:30"]), "fy": [2026],
                      "demand_mw": [1000.04], "seasonal_naive": [990.06], "no_weather": [1.0], "with_weather": [2.0],
                      "p10": [3.0], "p90": [4.0]})
    r = forecast_halfhour(f, REGIONS).iloc[0]
    assert r["interval_start"] == "2025-07-01 00:30:00"
    assert (r["demand_mw"], r["seasonal_naive"]) == (1000.0, 990.1)
    assert r["region_name"] == "South Australia"


def test_oversize_file_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr("pipeline.export_looker.MAX_UPLOAD_MB", 0)
    with pytest.raises(ValueError, match="upload limit"):
        write_csv(pd.DataFrame({"a": [1]}), tmp_path / "x.csv")


REAL = Path("looker/forecast_halfhour.csv")


@pytest.mark.skipif(not REAL.exists(), reason="exports not built")
def test_real_exports_reconcile_to_source():
    src = pd.read_parquet("data/star/fact_forecast.parquet")
    fc = pd.read_csv(REAL)
    assert len(fc) == len(src)
    # Rounding moves each row by at most 0.05 MW
    assert abs(fc["demand_mw"].sum() - src["demand_mw"].sum()) <= 0.05 * len(src)
    ins = pd.read_csv("looker/insights_region_fy.csv")
    saving = next(r["saving_aud_per_mw_year"] for r in json.loads(Path("validation/golden_values.json").read_text())["load_shift"]
                  if r["region_code"] == "SA1" and r["fy"] == 2026)
    got = ins[(ins["region_name"] == "South Australia") & (ins["financial_year"] == "FY2026")]["saving_aud_per_mw_year"].item()
    assert got == pytest.approx(saving)
    assert ins["financial_year"].min() == "FY2023" and ins["financial_year"].max() == "FY2026"
    # Actuals tie back to the 5-minute star schema: half-hourly MW x 0.5 = MWh
    energy = duckdb.connect().execute("""SELECT sum(energy_mwh) FROM 'data/star/fact_market.parquet' f
        JOIN 'data/star/dim_date.parquet' d USING (date_key) WHERE d.financial_year = 2026""").fetchone()[0]
    latest = fc[fc["financial_year"] == "FY2026"]
    assert latest["demand_mw"].sum() * 0.5 == pytest.approx(energy, abs=0.05 * 0.5 * len(latest))
