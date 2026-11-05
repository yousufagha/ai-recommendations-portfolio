import json
from pathlib import Path

import duckdb
import pytest
from pipeline.split_rents import READ, split

HEADER = "contract_start_date,contract_id,line_number,project_name_en\n"
ROWS = ('2025-07-01,CNT1,1,"VIEW 1,2"\n', "2025-07-02,CNT2,1,\n", "2001-02-15,CNT3,1,OLD\n", "2205-07-16,CNT4,1,LATE\n")


def source(tmp_path):
    a = tmp_path / "a.csv"
    a.write_text(HEADER + "".join(ROWS))
    return a


def test_keeps_every_row_and_buckets_odd_years(tmp_path):
    m = split([source(tmp_path)], tmp_path / "out")
    assert m["source_rows"] == 4
    assert {f["file"]: f["rows"] for f in m["files"]} == {
        "rents_2025.csv.gz": 2, "rents_pre-2008.csv.gz": 1, "rents_after-2027.csv.gz": 1}


def test_quoted_commas_survive(tmp_path):
    split([source(tmp_path)], tmp_path / "out")
    rows = duckdb.connect().execute(f"SELECT project_name_en FROM read_csv('{tmp_path}/out/rents_2025.csv.gz', {READ})").fetchall()
    assert ("VIEW 1,2",) in rows


def test_large_year_is_cut_into_parts(tmp_path):
    a = tmp_path / "a.csv"
    a.write_text(HEADER + "".join(f"2025-01-{i % 28 + 1:02d},{i:x},1,{i * 7919 % 104729:x}\n" for i in range(40000)))
    import pipeline.split_rents as s
    original = s.MAX_MB
    s.MAX_MB = 0.2
    try:
        m = split([a], tmp_path / "out")
    finally:
        s.MAX_MB = original
    assert len(m["files"]) > 1 and sum(f["rows"] for f in m["files"]) == 40000


MANIFEST = Path("data/raw/rents/manifest.json")


@pytest.mark.skipif(not MANIFEST.exists(), reason="raw files absent")
def test_committed_files_match_the_manifest():
    m = json.loads(MANIFEST.read_text())
    assert sum(f["rows"] for f in m["files"]) == m["source_rows"]
    for f in m["files"]:
        path = MANIFEST.parent / f["file"]
        assert path.stat().st_size < 100e6
        assert duckdb.connect().execute(f"SELECT count(*) FROM read_csv('{path}', {READ})").fetchone()[0] == f["rows"]
