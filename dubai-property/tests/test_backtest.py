import numpy as np
import pandas as pd
import pytest
from pipeline.backtest import decide, excess, permutation, price_changes, score, verdict, window


def sale(date, project, value, area_id="1", size=100.0, rooms="2 B/R"):
    return {"date": date, "value": value, "size": size, "area_id": area_id, "area": "A" + area_id, "project": project, "rooms": rooms,
            "type": "Flat", "stage": "ready", "buyers": 1}


def contract(start, project, rent, area_id="1", size=100.0, rooms="2 B/R"):
    return {"start": start, "rent": rent, "size": size, "area_id": area_id, "area": "A" + area_id, "project": project, "tenant": "Person", "rooms": rooms, "type": "Flat"}


def market(area_id, project, rent):
    sales = [sale(f"2022-0{m}-15", project, 2_100_000, area_id) for m in range(1, 10) for _ in range(5)]
    rents = [contract(f"2022-0{m}-15", project, rent, area_id) for m in range(1, 10) for _ in range(5)]
    return sales, rents


def test_records_after_the_decision_cannot_change_the_picks():
    s1, r1 = market("1", "P", 120_000)
    s2, r2 = market("2", "Q", 100_000)
    sales, rents = pd.DataFrame(s1 + s2), pd.DataFrame(r1 + r2)
    before, _, _ = decide("2022-11-03", rents, sales)
    future_rents = pd.DataFrame([contract("2022-11-04", "Q", 900_000, "2")] * 50)
    future_sales = pd.DataFrame([sale("2022-11-04", "Q", 2_000_000, "2")] * 50)
    after, _, _ = decide("2022-11-03", pd.concat([rents, future_rents]), pd.concat([sales, future_sales]))
    pd.testing.assert_frame_equal(before, after)
    assert before.sort_values("yield_pct")["area_id"].iloc[-1] == "1"


def test_price_change_ignores_mix_between_projects():
    rows = []
    for _ in range(5):
        rows += [sale("2022-01-15", "CHEAP", 1_000_000), sale("2022-01-15", "DEAR", 3_000_000),
                 sale("2022-08-15", "CHEAP", 1_100_000), sale("2022-08-15", "DEAR", 3_300_000),
                 sale("2022-08-15", "NEW", 9_000_000)]
    out = price_changes(pd.DataFrame(rows), ("2022-01-01", "2022-02-01"), ("2022-08-01", "2022-09-01"))
    assert out.iloc[0]["change_pct"] == pytest.approx(np.log(1.1) * 100)


def test_price_change_can_leave_out_near_line_sales():
    rows = [sale("2022-01-15", "P", 2_100_000), sale("2022-08-15", "P", 2_100_000)] * 3
    out = price_changes(pd.DataFrame(rows), ("2022-01-01", "2022-02-01"), ("2022-08-01", "2022-09-01"), drop_near=True)
    assert out.empty


def test_realised_rent_not_the_estimate_scores_the_return():
    table = pd.DataFrame({"area_id": ["1"], "rooms": ["2 B/R"], "price_aed": [2_000_000], "rent_aed": [100_000], "yield_pct": [5.0]})
    realised = pd.Series({("1", "2 B/R"): 140_000.0}, name="rent").rename_axis(["area_id", "rooms"])
    change = pd.DataFrame({"area_id": ["1"], "rooms": ["2 B/R"], "change_pct": [3.0], "matched": [10]})
    row = score(table, realised, change).iloc[0]
    assert row["realised_yield"] == pytest.approx(7.0) and row["total"] == pytest.approx(10.0)


def test_excess_compares_picks_with_the_others_only():
    d = pd.DataFrame({"yield_pct": [9.0, 8.0, 7.0], "total": [10.0, 20.0, 6.0]})
    assert excess(d, top=2) == 9.0


def test_excess_has_no_answer_when_picks_are_the_whole_set():
    assert excess(pd.DataFrame({"yield_pct": [9.0], "total": [10.0]}), top=5) is None


def test_permutation_flags_nothing_when_all_options_are_equal():
    frame = pd.DataFrame({"total": [1.0] * 12})
    out = permutation([frame], 0.0, draws=50)
    assert out["share_of_random_at_least_as_good"] == 1.0


def test_verdict_needs_both_windows_to_beat_chance():
    ahead = {"observed_points": 5.0, "random_95th_points": 4.0}
    behind = {"observed_points": 3.0, "random_95th_points": 4.0}
    r = [{"tested": True, "excess_plan_points": 1.0, "excess_centred_points": -1.0, "as_planned_excess_points": 1.0, "as_planned_near_line_weights_excess_points": -1.0}]
    assert verdict(r, {"plan": ahead, "centred": behind})["label"] == "not shown"
    assert verdict(r, {"plan": ahead, "centred": ahead})["shown"] is True


def test_window_starts_the_day_after():
    assert window("2022-11-03", -6, 0) == ("2022-05-04", "2022-11-03")
