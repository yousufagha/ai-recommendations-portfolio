"""Split the data.dubai rent contract CSVs into compressed yearly files under GitHub's 100 MB limit.

All columns and rows are kept as published, as text. Files follow the contract start year. Starts before 2008 share a
file, as do the few dated after 2027. A year too large for one file is cut into equal parts. The script fails if any
row or value changes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

from pipeline.split_raw import sha256

MAX_MB = 95
FIRST_YEAR = 2008
LAST_YEAR = 2027
READ = "header=true, all_varchar=true, delim=',', quote='\"', escape='\"'"


def _fingerprint(con, source: str) -> tuple:
    """Row count and an order-free checksum of every value, so any changed value is caught."""
    return con.execute(f"SELECT count(*), sum(hash(t)::HUGEINT) FROM read_csv({source}, {READ}) t").fetchone()


def _write(con, year: str, out: Path) -> list[dict]:
    parts = 1
    while True:
        written = []
        for part in range(1, parts + 1):
            name = f"rents_{year}.csv.gz" if parts == 1 else f"rents_{year}_part{part}.csv.gz"
            path = out / name
            con.execute(f"""COPY (SELECT * EXCLUDE (file_year, part) FROM (
                                SELECT *, ntile({parts}) OVER (ORDER BY contract_start_date, contract_id, line_number) AS part
                                FROM y WHERE file_year = '{year}') WHERE part = {part})
                            TO '{path}' (FORMAT csv, HEADER, FORCE_QUOTE *, COMPRESSION gzip)""")
            written.append(path)
        sizes = [p.stat().st_size / 1e6 for p in written]
        if max(sizes) <= MAX_MB:
            return [{"file": p.name, "rows": con.execute(f"SELECT count(*) FROM read_csv('{p}', {READ})").fetchone()[0],
                     "mb": round(s, 1)} for p, s in zip(written, sizes)]
        for p in written:
            p.unlink()
        parts += 1


def split(sources: list[Path], out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    names = "[" + ", ".join(f"'{s}'" for s in sources) + "]"
    con.execute(f"""CREATE VIEW y AS SELECT *, CASE
                        WHEN left(contract_start_date, 4) > '{LAST_YEAR}' THEN 'after-{LAST_YEAR}'
                        WHEN left(contract_start_date, 4) >= '{FIRST_YEAR}' THEN left(contract_start_date, 4)
                        ELSE 'pre-{FIRST_YEAR}' END AS file_year
                    FROM read_csv({names}, {READ})""")
    files = []
    for (year,) in con.execute("SELECT DISTINCT file_year FROM y ORDER BY 1").fetchall():
        files += _write(con, year, out)
    before = _fingerprint(con, names)
    after = _fingerprint(con, "[" + ", ".join(f"'{out / f['file']}'" for f in files) + "]")
    if before != after:
        raise ValueError(f"Rows or values changed during the split: {before} became {after}")
    return {"source_rows": before[0], "sources": [{"file": s.name, "sha256": sha256(s)} for s in sources], "files": files}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("sources", nargs="+", type=Path)
    p.add_argument("--out", default="data/raw/rents", type=Path)
    a = p.parse_args()
    manifest = split(a.sources, a.out)
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(manifest["source_rows"], "rows,", round(sum(f["mb"] for f in manifest["files"]), 1), "MB in", len(manifest["files"]), "files")
