import json
from pathlib import Path

import pandas as pd
import pytest
from pipeline.rent_yields import compare, estimate_rents, fit_beta, options, rank_ready


def contracts(project, n, rent, size=100, area_id="1", rooms="2 B/R"):
    return pd.DataFrame({"area_id": area_id, "rooms": rooms, "type": "Flat", "project": [project] * n, "rent": [rent] * n, "size": [size] * n, "start": "2026-01-01"})


def sold(project, n, value, stage="ready", size=100, area_id="1", rooms="2 B/R"):
    return pd.DataFrame({"area_id": area_id, "area": "A", "rooms": rooms, "type": "Flat", "project": [project] * n, "value": [value] * n, "size": [size] * n, "stage": stage, "buyers": 1})


def test_project_evidence_wins():
    out = estimate_rents(sold("P", 5, 2_100_000), contracts("P", 25, 120_000), sold("P", 5, 2_100_000), 0.7)
    assert set(out["level"]) == {"project"} and out["rent"].iloc[0] == 120_000


def test_same_price_tier_is_used_before_the_whole_area():
    rents = pd.concat([contracts(p, 12, 100_000) for p in "QRS"] + [contracts("LUX", 100, 300_000)])
    sales = pd.concat([sold(p, 5, 2_000_000) for p in "QRS"] + [sold("LUX", 5, 9_000_000)])
    out = estimate_rents(sold("P", 5, 2_100_000), rents, sales, 0.7)
    assert set(out["level"]) == {"price_tier"} and out["rent"].iloc[0] == 100_000


def test_area_rent_is_adjusted_down_for_a_cheaper_home():
    sales = sold("LUX", 5, 4_000_000)
    out = estimate_rents(sold("P", 5, 2_000_000), contracts("LUX", 40, 200_000), sales, 1.0)
    assert set(out["level"]) == {"area_adjusted"} and out["rent"].iloc[0] == pytest.approx(100_000)


def test_contracts_for_a_different_size_do_not_count():
    out = estimate_rents(sold("P", 5, 2_100_000), contracts("P", 25, 120_000, size=200), sold("P", 5, 2_100_000), 0.7)
    assert set(out["level"]) == {"none"}


def test_no_evidence_gives_no_estimate_and_no_option():
    near = sold("P", 40, 2_100_000)
    out = estimate_rents(near, contracts("P", 5, 120_000), near, 0.7)
    assert set(out["level"]) == {"none"} and options(out, contracts("P", 5, 120_000), near).empty


def test_beta_reads_rent_against_price_within_an_area():
    rents = pd.concat([contracts("P", 25, 100_000), contracts("Q", 25, 200_000)])
    sales = pd.concat([sold("P", 5, 1_000_000), sold("Q", 5, 2_000_000)])
    assert fit_beta(rents, sales) == pytest.approx(1.0)


def test_yield_is_rent_over_price():
    near = sold("P", 40, 2_000_000)
    rents = contracts("P", 25, 120_000)
    row = options(estimate_rents(near, rents, near, 0.7), rents, near).iloc[0]
    assert row["yield_pct"] == 6.0 and row["low_pct"] == row["high_pct"] == 6.0 and row["all_price_yield_pct"] == 6.0


def test_only_ready_flats_on_project_evidence_are_ranked():
    base = {"type": "Flat", "low_pct": 5.0, "high_pct": 6.0, "yield_pct": 5.5, "project_share": 0.9, "stage": "ready"}
    table = pd.DataFrame([base, {**base, "project_share": 0.1}, {**base, "stage": "off_plan"}, {**base, "type": "Villa"},
                          {**base, "yield_pct": 1.5}])
    ranked, thin = rank_ready(table, 0.5)
    assert len(ranked) == 2 and len(thin) == 1 and ranked["top_tier"].tolist() == [True, False]


def test_compare_reports_no_shared_options():
    empty = pd.DataFrame(columns=["stage", "area_id", "rooms", "type", "yield_pct"])
    assert compare(empty, empty) == {"options": 0}


RESULTS = Path("validation/rent_yields.json")


@pytest.mark.skipif(not RESULTS.exists(), reason="results absent")
def test_published_results_hold_only_aggregates_and_ranked_options_meet_the_rules():
    text = RESULTS.read_text()
    assert "CNT" not in text and "contract_id" not in text
    ranked = json.loads(text)["ready_ranked"]
    assert all(r["stage"] == "ready" and r["type"] == "Flat" and r["project_share"] >= 0.5 and r["sales"] >= 30 for r in ranked)
    assert [r["yield_pct"] for r in ranked] == sorted((r["yield_pct"] for r in ranked), reverse=True)
