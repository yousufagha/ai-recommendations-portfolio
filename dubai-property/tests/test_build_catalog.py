import json
from pathlib import Path

from pipeline.build_catalog import RAW, build

ROOT = Path(__file__).resolve().parents[2]


def test_catalog_matches_the_files_in_the_repo():
    saved = json.loads((ROOT / "docs" / "data-catalog.json").read_text())
    assert saved == build(ROOT)


def test_every_entry_points_to_a_real_file():
    for dataset in build(ROOT)["datasets"]:
        assert dataset["files"], dataset["name"]
        for f in dataset["files"]:
            assert f["url"].startswith(RAW)
            assert (ROOT / f["url"].removeprefix(RAW)).stat().st_size == f["bytes"]


def test_row_totals_are_stated_for_the_large_dubai_files():
    totals = {d["name"]: d.get("rows") for d in build(ROOT)["datasets"]}
    assert totals["Dubai real estate transactions"] == 1_813_436
    assert totals["Dubai rent contracts"] == 10_683_846
