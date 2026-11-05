import numpy as np
import pandas as pd
from pipeline.forecast import LAGS, add_features, backtest_region, metrics


def frame(days=800, region="VIC1"):
    ts = pd.date_range("2022-01-01", periods=days * 48, freq="30min")
    rng = np.random.default_rng(0)
    slot = ts.hour * 2 + ts.minute // 30
    demand = 5000 + 800 * np.sin(slot / 48 * 2 * np.pi) + rng.normal(0, 50, len(ts))
    return pd.DataFrame({"region_code": region, "interval_start": ts, "demand_mw": demand,
                         "temp_c": 20 + rng.normal(0, 3, len(ts)), "radiation": 100.0})


def test_all_lags_are_at_least_one_day():
    assert min(LAGS) >= 48


def test_target_day_demand_cannot_reach_its_own_lag_features():
    df = frame(40)
    day = pd.Timestamp("2022-01-30")
    changed = df.copy()
    changed.loc[changed["interval_start"].dt.normalize() == day, "demand_mw"] = 1e9
    cols = [f"lag_{l}" for l in LAGS] + ["mean_prior_7d"]
    a = add_features(df)
    b = add_features(changed)
    mask = a["interval_start"].dt.normalize() == day
    pd.testing.assert_frame_equal(a.loc[mask, cols], b.loc[mask, cols])


def test_mean_prior_changes_on_following_day():
    df = frame(40)
    changed = df.copy()
    changed.loc[changed["interval_start"].dt.normalize() == pd.Timestamp("2022-01-30"), "demand_mw"] = 1e9
    next_day = pd.Timestamp("2022-01-31")
    b = add_features(changed)
    assert b.loc[b["interval_start"].dt.normalize() == next_day, "mean_prior_7d"].iloc[0] > 1e7


def test_local_hour_follows_daylight_saving_but_slot_does_not():
    df = frame(200)
    f = add_features(df)
    summer = f[f["interval_start"] == pd.Timestamp("2022-01-15 12:00")].iloc[0]
    winter = f[f["interval_start"] == pd.Timestamp("2022-06-15 12:00")].iloc[0]
    assert summer["slot"] == winter["slot"] == 24
    assert summer["local_hour"] == 13
    assert winter["local_hour"] == 12


def test_backtest_only_trains_on_earlier_years_and_beats_nothing_silly():
    r = backtest_region(frame(), test_fys=[2024])
    assert r["fy"].unique().tolist() == [2024]
    m = metrics(r)[0]
    assert m["no_weather_wape"] < 0.05
    assert 0.5 < m["p10_p90_coverage"] < 1
