"""Figures behind the landing page charts: market size, rents, and sales around AED 2 million."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import pandas as pd

from pipeline.split_rents import READ
from pipeline.value_at_line import load

BAND = 25_000
COMPARISON_LINES = (1_500_000, 2_500_000, 3_000_000)


def _ratio(values: pd.Series, line: int, width: int = 50_000) -> tuple[int, int]:
    return int(((values >= line - width) & (values < line)).sum()), int(((values >= line) & (values < line + width)).sum())


def _share(above: int, below: int) -> float | None:
    return round(above / below, 2) if below else None


def sales_by_year(df: pd.DataFrame) -> list[dict]:
    counts = df[df["year"] >= "2015"].groupby("year").size()
    return [{"year": y, "sales": int(n)} for y, n in counts.items()]


def bands_around_line(df: pd.DataFrame, year: str = "2025", line: int = 2_000_000, span: int = 200_000) -> list[dict]:
    v = df.loc[(df["year"] == year) & (df["value"] >= line - span) & (df["value"] < line + span), "value"]
    bins = ((v // BAND) * BAND).astype(int).value_counts().sort_index()
    return [{"from_aed": int(b), "sales": int(n)} for b, n in bins.items()]


def quarterly_crowding(df: pd.DataFrame, first_year: str = "2021") -> list[dict]:
    d = df[df["year"] >= first_year].copy()
    d["quarter"] = d["year"] + " Q" + ((d["date"].str[5:7].astype(int) - 1) // 3 + 1).astype(str)
    rows = []
    for quarter, part in d.groupby("quarter"):
        below, above = _ratio(part["value"], 2_000_000)
        pairs = [_ratio(part["value"], line) for line in COMPARISON_LINES]
        rows.append({"quarter": quarter, "at_2m": _share(above, below),
                     "comparison": _share(sum(p[1] for p in pairs), sum(p[0] for p in pairs))})
    return rows


def rents_by_year(raw: str) -> list[dict]:
    """Median yearly rent for single-property residential contracts. Bulk and whole-building contracts would distort it."""
    rows = duckdb.connect().execute(f"""
        SELECT left(contract_start_date, 4) AS year, ejari_property_type_en AS type, count(*) AS contracts,
               median(try_cast(annual_amount AS DOUBLE)) AS median_aed
        FROM read_csv('{raw}', {READ})
        WHERE property_usage_en = 'Residential' AND ejari_property_type_en IN ('Flat', 'Villa')
          AND try_cast(no_of_prop AS INT) = 1 AND try_cast(annual_amount AS DOUBLE) BETWEEN 5000 AND 5000000
          AND contract_start_date >= '2015' AND contract_start_date < '2027'
        GROUP BY 1, 2 ORDER BY 1, 2""").fetchall()
    return [{"year": y, "type": t, "contracts": n, "median_aed": round(m)} for y, t, n, m in rows]


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sales", default="data/raw/transactions/*.csv.gz")
    p.add_argument("--rents", default="data/raw/rents/*.csv.gz")
    p.add_argument("--out", default="validation/market_overview.json", type=Path)
    a = p.parse_args()
    sales = load(a.sales)
    out = {"sales_by_year": sales_by_year(sales), "bands_2025": bands_around_line(sales),
           "quarterly_crowding": quarterly_crowding(sales), "rents_by_year": rents_by_year(a.rents)}
    a.out.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out)[:1500])
