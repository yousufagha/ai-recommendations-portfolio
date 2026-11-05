import json
from pathlib import Path

import duckdb
import pytest
from pipeline.split_raw import split

HEADER = "instance_date,transaction_id,project_name_en\n"


def read(path):
    return duckdb.connect().execute(
        f"""SELECT * FROM read_csv('{path}', header=true, all_varchar=true, delim=',', quote='"', escape='"')"""
    ).fetchall()


def test_split_keeps_every_row_and_quoted_commas(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    a.write_text(HEADER + '2024-08-07,1-41-2024-1,"VIEW 1,2,3"\n1416-07-02,1-41-1416-1,OLD\n')
    b.write_text(HEADER + "2025-01-01,1-41-2025-1,NEW\n2007-12-31,1-41-2007-1,OLD2\n")
    m = split([a, b], tmp_path / "out")
    assert m["source_rows"] == 4
    assert {f["file"]: f["rows"] for f in m["files"]} == {
        "transactions_2024.csv.gz": 1, "transactions_2025.csv.gz": 1, "transactions_pre-2008.csv.gz": 2}
    assert read(tmp_path / "out" / "transactions_2024.csv.gz") == [("2024-08-07", "1-41-2024-1", "VIEW 1,2,3")]


def test_oversize_file_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr("pipeline.split_raw.MAX_MB", 0)
    a = tmp_path / "a.csv"
    a.write_text(HEADER + "2024-08-07,x,y\n")
    with pytest.raises(ValueError, match="over"):
        split([a], tmp_path / "out")


MANIFEST = Path("data/raw/transactions/manifest.json")


@pytest.mark.skipif(not MANIFEST.exists(), reason="raw files absent")
def test_committed_files_match_the_manifest():
    m = json.loads(MANIFEST.read_text())
    assert sum(f["rows"] for f in m["files"]) == m["source_rows"]
    n = duckdb.connect().execute(
        f"""SELECT count(*), count(DISTINCT transaction_id) FROM read_csv('{MANIFEST.parent}/*.csv.gz', header=true,
            all_varchar=true, delim=',', quote='"', escape='"')"""
    ).fetchone()
    assert n == (m["source_rows"], m["source_rows"])
