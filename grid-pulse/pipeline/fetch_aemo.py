"""Download AEMO monthly price and demand files for every NEM region.

Source: AEMO, used under its general copyright permission, with attribution.
Files already on disk are skipped, except the most recent month, which AEMO may still revise.
"""
from __future__ import annotations

import argparse
import datetime as dt
import time
from pathlib import Path

import requests

REGIONS = ["NSW1", "QLD1", "SA1", "TAS1", "VIC1"]
URL = "https://aemo.com.au/aemo/data/nem/priceanddemand/PRICE_AND_DEMAND_{ym}_{region}.csv"
HEADER = "REGION,SETTLEMENTDATE,TOTALDEMAND,RRP,PERIODTYPE"


def months(start: dt.date, end: dt.date):
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        yield f"{y}{m:02d}"
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def last_complete_month(today: dt.date) -> dt.date:
    return today.replace(day=1) - dt.timedelta(days=1)


def fetch(start: dt.date, end: dt.date, out: Path, session: requests.Session) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    stats = {"downloaded": 0, "skipped": 0}
    final = f"{end.year}{end.month:02d}"
    for ym in months(start, end):
        for region in REGIONS:
            path = out / f"{ym}_{region}.csv"
            if path.exists() and ym != final:
                stats["skipped"] += 1
                continue
            r = session.get(URL.format(ym=ym, region=region), timeout=60)
            r.raise_for_status()
            if not r.text.startswith(HEADER):
                raise ValueError(f"Unexpected content for {ym} {region}: {r.text[:80]!r}")
            path.write_bytes(r.content)
            stats["downloaded"] += 1
            time.sleep(0.1)
    return stats


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2019-01-01", type=dt.date.fromisoformat)
    p.add_argument("--end", default=None, type=dt.date.fromisoformat)
    p.add_argument("--out", default="data/raw/aemo", type=Path)
    a = p.parse_args()
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (grid-pulse portfolio project)"
    print(fetch(a.start, a.end or last_complete_month(dt.date.today()), a.out, s))
