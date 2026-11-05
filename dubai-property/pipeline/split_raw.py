"""Split the two data.dubai transaction CSVs into compressed yearly files under GitHub's 100 MB limit.

All columns and rows are kept as published, as text. Rows dated before 2008 are thin and hold some
non-Gregorian dates (such as 1416-07-02), so they share one file. The manifest records row counts and
the checksums of the source files, and the script fails if any row goes missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb

MAX_MB = 95
FIRST_YEAR = 2008


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def split(sources: list[Path], out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    names = ", ".join(f"'{s}'" for s in sources)
    con.execute(f"CREATE VIEW t AS SELECT * FROM read_csv([{names}], header=true, all_varchar=true, union_by_name=true)")
    con.execute(f"""CREATE VIEW y AS SELECT *, CASE WHEN left(instance_date, 4) >= '{FIRST_YEAR}'
                    THEN left(instance_date, 4) ELSE 'pre-{FIRST_YEAR}' END AS file_year FROM t""")
    total = con.execute("SELECT count(*) FROM t").fetchone()[0]
    files = []
    for (year,) in con.execute("SELECT DISTINCT file_year FROM y ORDER BY 1").fetchall():
        path = out / f"transactions_{year}.csv.gz"
        con.execute(f"""COPY (SELECT * EXCLUDE file_year FROM y WHERE file_year = '{year}'
                        ORDER BY instance_date, transaction_id) TO '{path}' (FORMAT csv, HEADER, COMPRESSION gzip)""")
        mb = path.stat().st_size / 1e6
        if mb > MAX_MB:
            raise ValueError(f"{path.name} is {mb:.1f} MB, over {MAX_MB} MB")
        rows = con.execute(f'''SELECT count(*) FROM read_csv('{path}', header=true, all_varchar=true, delim=',', quote='"', escape='"')''').fetchone()[0]
        files.append({"file": path.name, "rows": rows, "mb": round(mb, 1)})
    if sum(f["rows"] for f in files) != total:
        raise ValueError("Row count changed during the split")
    return {"source_rows": total, "sources": [{"file": s.name, "sha256": sha256(s)} for s in sources], "files": files}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("sources", nargs="+", type=Path)
    p.add_argument("--out", default="data/raw/transactions", type=Path)
    a = p.parse_args()
    manifest = split(a.sources, a.out)
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(manifest["source_rows"], "rows,", sum(f["mb"] for f in manifest["files"]), "MB in", len(manifest["files"]), "files")
