"""Clean rent contracts down to evidence of what a single home rents for on the open market today.

Renewals are left out because they lag the market: in 2025 new flat contracts averaged AED 971 per square metre
against AED 693 for renewals. Only aggregates of this data should leave the project, so contract IDs are dropped here.
"""
from __future__ import annotations

import duckdb
import pandas as pd

from pipeline.split_rents import READ

DATA_CUT = "2026-11-03"
BEDROOMS = {"Studio": "Studio", "1bed room+Hall": "1 B/R", "2 bed rooms+hall": "2 B/R", "3 bed rooms+hall": "3 B/R",
            "4 bed rooms+hall": "4 B/R", "5 bed rooms+hall": "5 B/R", "6 bed rooms+hall": "6 B/R", "7 bed rooms+hall": "7 B/R"}
_DAYS = "date_diff('day', try_cast(contract_start_date AS DATE), try_cast(contract_end_date AS DATE))"
_AMOUNT = "try_cast(annual_amount AS DOUBLE)"
_SIZE = "try_cast(actual_area AS DOUBLE)"


def clean(raw: str, since: str = "2015-01-01", cut: str = DATA_CUT) -> tuple[pd.DataFrame, dict]:
    """Return usable new contracts and how many lines survive each step."""
    names = ", ".join(f"'{k}'" for k in BEDROOMS)
    steps = [("in_period", f"contract_start_date >= '{since}' AND contract_start_date <= '{cut}'"),
             ("residential", "property_usage_en = 'Residential'"),
             ("flat_or_villa", "ejari_property_type_en IN ('Flat', 'Villa')"),
             ("single_property", "try_cast(no_of_prop AS INT) = 1"),
             ("about_a_year", f"{_DAYS} BETWEEN 330 AND 400"),
             ("plausible_rent", f"{_AMOUNT} BETWEEN 5000 AND 5000000"),
             ("plausible_size", f"{_SIZE} BETWEEN 15 AND 2000"),
             ("known_bedrooms", f"ejari_property_sub_type_en IN ({names})"),
             ("new_contract", "contract_reg_type_en = 'New'")]
    con = duckdb.connect()
    so_far, counts = [], []
    for name, condition in steps:
        so_far.append(f"({condition})")
        counts.append(f"count(*) FILTER (WHERE {' AND '.join(so_far)}) AS {name}")
    source = f"read_csv('{raw}', {READ})"
    row = con.execute(f"SELECT count(*) AS all_lines, {', '.join(counts)} FROM {source}").df().iloc[0]
    funnel = {k: int(v) for k, v in row.items()}
    rows = con.execute(f"""
        SELECT contract_start_date AS start, {_AMOUNT} AS rent, {_SIZE} AS size, area_id, area_name_en AS area,
               nullif(trim(project_number), '') AS project, ejari_property_sub_type_en AS sub_type,
               ejari_property_type_en AS type, tenant_type_en AS tenant
        FROM {source} WHERE {' AND '.join(so_far)}
        QUALIFY row_number() OVER (PARTITION BY contract_id ORDER BY try_cast(line_number AS INT)) = 1""").df()
    rows["rooms"] = rows.pop("sub_type").map(BEDROOMS)
    funnel["one_line_per_contract"] = len(rows)
    return rows, funnel
