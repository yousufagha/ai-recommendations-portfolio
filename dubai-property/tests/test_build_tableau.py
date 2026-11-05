import csv
import json

from pipeline.build_tableau import ROOT, tables, write

OUT = ROOT / "tableau"


def read(name):
    with (OUT / f"{name}.csv").open() as f:
        return list(csv.DictReader(f))


def test_committed_files_match_the_results():
    expected = tables()
    for name, rows in expected.items():
        saved = read(name)
        assert len(saved) == len(rows), name
        assert saved == [{k: "" if v is None else str(v) for k, v in row.items()} for row in rows], name


def test_files_hold_every_option_and_the_ranking_is_kept():
    results = json.loads((ROOT / "validation" / "rent_yields.json").read_text())
    rows = tables()["options"]
    assert len(rows) == sum(len(results[k]) for k in ("ready_ranked", "ready_indicative", "off_plan_indicative", "villas_not_ranked"))
    assert sum(r["top_tier"] for r in rows) == sum(x["top_tier"] for x in results["ready_ranked"])
    assert all(r["group"] == "Ready, ranked" for r in rows if r["top_tier"])


def test_untested_round_is_marked():
    rounds = {r["decision"]: r for r in tables()["backtest_rounds"]}
    assert rounds["2021-11-03"]["tested"] is False and rounds["2021-11-03"]["total_gap_first_price_measure"] is None


def test_no_contract_level_data_leaves_the_project(tmp_path):
    write(tmp_path)
    for path in tmp_path.glob("*.csv"):
        text = path.read_text()
        assert "contract_id" not in text and "CNT" not in text and "tenant" not in text
