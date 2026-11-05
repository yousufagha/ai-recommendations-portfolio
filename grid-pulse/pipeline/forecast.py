"""Day-ahead half-hourly demand forecast with an expanding-window backtest.

Issue time is midnight market time before the target day, so every lag is at least 48 half-hours old.
Hyperparameters are fixed, not tuned, so test folds cannot leak into model choice.
Observed weather stands in for a weather forecast, which makes the weather model optimistic. The
no-weather model is reported beside it to bound that optimism.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb
import holidays
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

TIMEZONES = {"NSW1": "Australia/Sydney", "QLD1": "Australia/Brisbane", "SA1": "Australia/Adelaide",
             "TAS1": "Australia/Hobart", "VIC1": "Australia/Melbourne"}
SUBDIVISIONS = {"NSW1": "NSW", "QLD1": "QLD", "SA1": "SA", "TAS1": "TAS", "VIC1": "VIC"}
SLOTS_PER_DAY = 48
LAGS = [SLOTS_PER_DAY, 2 * SLOTS_PER_DAY, 7 * SLOTS_PER_DAY, 14 * SLOTS_PER_DAY]
TEST_FYS = [2024, 2025, 2026]
CALENDAR = ["slot", "local_hour", "day_of_week", "month", "is_weekend", "is_holiday", "day_of_year"]
WEATHER = ["temp_c", "cooling_degrees", "heating_degrees", "radiation"]
BALANCE = 18.0
CALIBRATION_DAYS = 365
RANGE_COVERAGE = 0.8


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """df has one region: interval_start (market time, sorted, no gaps) and demand_mw."""
    region = df["region_code"].iloc[0]
    out = df.copy()
    for lag in LAGS:
        out[f"lag_{lag}"] = out["demand_mw"].shift(lag)
    # Mean of the 7 complete days before the target day, so nothing from the target day enters.
    daily = out.groupby(out["interval_start"].dt.normalize())["demand_mw"].mean()
    out["mean_prior_7d"] = out["interval_start"].dt.normalize().map(daily.shift(1).rolling(7).mean())

    ts = out["interval_start"]
    local = ts.dt.tz_localize("Etc/GMT-10").dt.tz_convert(ZoneInfo(TIMEZONES[region]))
    hols = holidays.Australia(subdiv=SUBDIVISIONS[region], years=range(ts.dt.year.min(), ts.dt.year.max() + 1))
    out["slot"] = ts.dt.hour * 2 + ts.dt.minute // 30
    out["local_hour"] = local.dt.hour + local.dt.minute / 60
    out["day_of_week"] = ts.dt.day_of_week
    out["month"] = ts.dt.month
    out["day_of_year"] = ts.dt.day_of_year
    out["is_weekend"] = (ts.dt.day_of_week >= 5).astype(int)
    out["is_holiday"] = ts.dt.date.map(lambda d: d in hols).astype(int)
    if "temp_c" in out:
        out["cooling_degrees"] = (out["temp_c"] - BALANCE).clip(lower=0)
        out["heating_degrees"] = (BALANCE - out["temp_c"]).clip(lower=0)
    return out


def fiscal_year(ts: pd.Series) -> pd.Series:
    return ts.dt.year + (ts.dt.month >= 7).astype(int)


def _model(loss: str = "squared_error", **kw) -> HistGradientBoostingRegressor:
    return HistGradientBoostingRegressor(loss=loss, max_iter=300, learning_rate=0.06, max_leaf_nodes=48,
                                         min_samples_leaf=40, l2_regularization=1.0, random_state=42, **kw)


def backtest_region(df: pd.DataFrame, test_fys=TEST_FYS) -> pd.DataFrame:
    feats = add_features(df).dropna(subset=[f"lag_{l}" for l in LAGS] + ["mean_prior_7d"])
    feats = feats.assign(fy=fiscal_year(feats["interval_start"]))
    lag_cols = [f"lag_{l}" for l in LAGS] + ["mean_prior_7d"]
    base = lag_cols + CALENDAR
    full = base + WEATHER
    results = []
    for fy in test_fys:
        train, test = feats[feats["fy"] < fy], feats[feats["fy"] == fy]
        if test.empty:
            continue
        r = test[["region_code", "interval_start", "demand_mw", "fy"]].copy()
        r["seasonal_naive"] = test[f"lag_{7 * SLOTS_PER_DAY}"]
        r["no_weather"] = _model().fit(train[base], train["demand_mw"]).predict(test[base])
        r["with_weather"] = _model().fit(train[full], train["demand_mw"]).predict(test[full])
        # Conformal adjustment: widen the range using errors on the final training year, never the test year.
        cut = train["interval_start"].max() - pd.Timedelta(days=CALIBRATION_DAYS)
        fit, calib = train[train["interval_start"] <= cut], train[train["interval_start"] > cut]
        low = _model("quantile", quantile=0.1).fit(fit[base], fit["demand_mw"])
        high = _model("quantile", quantile=0.9).fit(fit[base], fit["demand_mw"])
        scores = np.maximum(low.predict(calib[base]) - calib["demand_mw"], calib["demand_mw"] - high.predict(calib[base]))
        margin = np.quantile(scores, RANGE_COVERAGE)
        r["p10"] = low.predict(test[base]) - margin
        r["p90"] = high.predict(test[base]) + margin
        results.append(r)
    return pd.concat(results, ignore_index=True)


def metrics(r: pd.DataFrame) -> list[dict]:
    rows = []
    peak = r["interval_start"].dt.hour.between(16, 20)
    for (region, fy), g in r.groupby(["region_code", "fy"]):
        row = {"region_code": region, "fy": int(fy), "rows": len(g)}
        for m in ["seasonal_naive", "no_weather", "with_weather"]:
            err = g[m] - g["demand_mw"]
            row[f"{m}_wape"] = round(float(err.abs().sum() / g["demand_mw"].abs().sum()), 4)
            row[f"{m}_mae_mw"] = round(float(err.abs().mean()), 1)
            row[f"{m}_bias_mw"] = round(float(err.mean()), 1)
            p = g[peak.loc[g.index]]
            row[f"{m}_peak_wape"] = round(float((p[m] - p["demand_mw"]).abs().sum() / p["demand_mw"].abs().sum()), 4)
        row["p10_p90_coverage"] = round(float(g["demand_mw"].between(g["p10"], g["p90"]).mean()), 4)
        rows.append(row)
    return rows


def load(star: Path, weather: Path) -> pd.DataFrame:
    con = duckdb.connect()
    d = con.execute(f"""
        SELECT region_code, time_bucket(INTERVAL 30 MINUTE, interval_start) AS interval_start,
               sum(energy_mwh) * 2 AS demand_mw
        FROM '{star}/fact_market.parquet' GROUP BY 1, 2 ORDER BY 1, 2
    """).df()
    frames = []
    for f in sorted(weather.glob("*.json")):
        b = json.loads(f.read_text())
        frames.append(pd.DataFrame({"region_code": b["region"], "weight": b["weight"],
                                    "hour": pd.to_datetime(b["hourly"]["time"]),
                                    "temp": b["hourly"]["temperature_2m"],
                                    "rad": b["hourly"]["shortwave_radiation"]}))
    w = pd.concat(frames)
    w["temp_w"], w["rad_w"] = w["temp"] * w["weight"], w["rad"] * w["weight"]
    w = w.groupby(["region_code", "hour"], as_index=False).agg(temp_c=("temp_w", "sum"), radiation=("rad_w", "sum"),
                                                               w=("weight", "sum"))
    if not np.isclose(w["w"], 1.0).all():
        raise ValueError("Weather weights must sum to 1 for every region and hour")
    d["hour"] = d["interval_start"].dt.floor("h")
    return d.merge(w.drop(columns="w"), on=["region_code", "hour"], how="left").drop(columns="hour")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--star", default="data/star", type=Path)
    p.add_argument("--weather", default="data/raw/weather", type=Path)
    a = p.parse_args()
    data = load(a.star, a.weather)
    missing = data["temp_c"].isna().sum()
    if missing > len(data) * 0.001:
        raise ValueError(f"{missing} rows have no weather")
    res = pd.concat([backtest_region(g.sort_values("interval_start").reset_index(drop=True))
                     for _, g in data.groupby("region_code")], ignore_index=True)
    res.to_parquet(a.star / "fact_forecast.parquet", index=False)
    Path("validation/forecast_metrics.json").write_text(json.dumps(metrics(res), indent=1))
    print("rows", len(res), "missing weather", int(missing))
