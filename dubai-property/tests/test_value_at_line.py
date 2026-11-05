import numpy as np
import pandas as pd
from pipeline.value_at_line import crowding, step_at_line, value_gap

LINE = 2_000_000


def sales(step=0.0, n=20000, seed=1):
    """Synthetic buildings where value follows size, with an optional jump in price at the line."""
    rng = np.random.default_rng(seed)
    building = rng.integers(0, 400, n)
    size = rng.uniform(60, 220, n)
    value = (9000 + building * 5) * size * np.exp(rng.normal(0, 0.03, n))
    value[(value >= LINE * 0.97) & (value < LINE)] *= 1 + step
    return pd.DataFrame({"place": building.astype(str), "year": "2025", "stage": "ready", "size": size, "value": value,
                         "date": "2025-01-01"})


def test_no_step_reads_near_zero():
    assert abs(step_at_line(value_gap(sales(), LINE), LINE)["step_pct"]) < 1


def test_a_real_step_is_recovered():
    df = sales()
    near_below = (df["value"] >= LINE * 0.97) & (df["value"] < LINE)
    df.loc[near_below, "value"] = LINE * 1.0001 * (df.loc[near_below, "value"] / (LINE * 0.97))
    r = step_at_line(value_gap(df, LINE), LINE)
    assert r["low_pct"] > 0


def test_near_sales_do_not_shape_the_estimate():
    df = sales()
    base = value_gap(df, LINE)
    changed = df.copy()
    near = np.log(changed["value"] / LINE).abs() <= 0.05
    changed.loc[near, "value"] *= 1.001
    again = value_gap(changed, LINE)
    assert np.allclose(base["log_value_centre"], again.loc[base.index, "log_value_centre"])


def test_sales_on_the_line_are_counted_apart():
    df = sales()
    df.loc[df.index[:300], "value"] = LINE
    r = step_at_line(value_gap(df, LINE), LINE)
    assert r["sales_on_line"] >= 300
    assert r["sales_near"] == len(value_gap(df, LINE)) - r["sales_on_line"]


def test_crowding_counts_each_side_of_the_price():
    df = pd.DataFrame({"date": ["2025-01-01"] * 3, "value": [1_990_000.0, 2_000_000.0, 2_049_000.0]})
    row = next(r for r in crowding(df) if r["line"] == LINE and r["period"] == "from_q2_2022")
    assert (row["below"], row["above"], row["ratio"]) == (1, 2, 2.0)
