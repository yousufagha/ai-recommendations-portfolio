"""Compute the evidence behind the Grid Pulse recommendations, and the golden values.

Computed directly from the star schema, so the live report can be checked against them.
All analysis figures are for Australian financial years (July to June) in the 5-minute era.
Battery values are perfect-foresight upper bounds, not forecasts of achievable revenue.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb

FIRST_FY = 2023  # first full financial year after the move to 5-minute settlement
CAP_STRIKES = [150, 300, 500]
EFFICIENCY = 0.85


def _base(con) -> None:
    con.execute(f"""
        CREATE OR REPLACE VIEW m AS
        SELECT f.*, d.financial_year AS fy, d.year, t.day_part, d.is_weekend
        FROM fact_market f JOIN dim_date d USING (date_key) JOIN dim_time t USING (time_key)
    """)
    con.execute(f"""
        CREATE OR REPLACE VIEW m5 AS
        SELECT * FROM m
        WHERE fy >= {FIRST_FY}
          AND fy IN (SELECT fy FROM m GROUP BY fy HAVING max(date_key) >= make_date(fy, 6, 30))
    """)


def _records(con, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, [round(v, 4) if isinstance(v, float) else v for v in row])) for row in cur.fetchall()]


def golden_values(con) -> list[dict]:
    return _records(con, """
        SELECT region_code, year,
               count(*) AS intervals,
               sum(energy_mwh) AS energy_mwh,
               sum(turnover_aud) AS turnover_aud,
               sum(turnover_aud) / sum(energy_mwh) AS energy_weighted_price,
               sum(price_aud_mwh * interval_minutes) / sum(interval_minutes) AS time_weighted_price,
               avg(price_aud_mwh) AS naive_row_average_price
        FROM m GROUP BY 1, 2 ORDER BY 1, 2
    """)


def cost_concentration(con) -> list[dict]:
    """Share of wholesale cost in the dearest 1% of intervals, by region and year."""
    return _records(con, """
        WITH r AS (
            SELECT region_code, fy, turnover_aud,
                   percent_rank() OVER (PARTITION BY region_code, fy ORDER BY price_aud_mwh DESC) AS pr
            FROM m5
        )
        SELECT region_code, fy,
               sum(turnover_aud) FILTER (WHERE pr < 0.01) / sum(turnover_aud) AS top_1pct_cost_share
        FROM r GROUP BY 1, 2 ORDER BY 1, 2
    """)


def cap_value(con) -> list[dict]:
    """Average $/MWh of load above each strike: the payoff of a cap, before any premium."""
    selects = ", ".join(
        f"sum(greatest(price_aud_mwh - {s}, 0) * energy_mwh) / sum(energy_mwh) AS cap_{s}_aud_mwh" for s in CAP_STRIKES
    )
    return _records(con, f"""
        SELECT region_code, fy, sum(turnover_aud) / sum(energy_mwh) AS energy_weighted_price, {selects}
        FROM m5 GROUP BY 1, 2 ORDER BY 1, 2
    """)


def load_shift(con) -> list[dict]:
    """Value of moving 1 MW for 4 hours a day from evening peak to solar window, weekdays only."""
    return _records(con, """
        WITH p AS (
            SELECT region_code, fy,
                   avg(price_aud_mwh) FILTER (WHERE day_part = 'Evening peak') AS evening,
                   avg(price_aud_mwh) FILTER (WHERE day_part = 'Solar') AS solar,
                   count(DISTINCT date_key) FILTER (WHERE NOT is_weekend) AS weekdays
            FROM m5 WHERE NOT is_weekend GROUP BY 1, 2
        )
        SELECT region_code, fy, evening AS evening_price, solar AS solar_price,
               evening - solar AS spread_aud_mwh,
               (evening - solar) * 4 * weekdays AS saving_aud_per_mw_year
        FROM p ORDER BY 1, 2
    """)


def battery_upper_bound(con) -> list[dict]:
    """1 MW, 2-hour battery, one cycle a day, perfect foresight, at half-hourly prices.

    Ignores charge-before-discharge ordering, degradation, price impact and fees,
    so the result is an upper bound on gross energy arbitrage.
    """
    return _records(con, f"""
        WITH hh AS (
            SELECT region_code, fy, date_key, time_key // 30 AS slot, avg(price_aud_mwh) AS price
            FROM m5 GROUP BY 1, 2, 3, 4
        ),
        ranked AS (
            SELECT *, row_number() OVER (PARTITION BY region_code, date_key ORDER BY price) AS lo,
                      row_number() OVER (PARTITION BY region_code, date_key ORDER BY price DESC) AS hi
            FROM hh
        ),
        daily AS (
            SELECT region_code, fy, date_key,
                   avg(price) FILTER (WHERE lo <= 4) AS charge,
                   avg(price) FILTER (WHERE hi <= 4) AS discharge
            FROM ranked GROUP BY 1, 2, 3
        )
        SELECT region_code, fy,
               sum(greatest(2 * discharge - 2 * charge / {EFFICIENCY}, 0)) AS gross_aud_per_mw_year
        FROM daily GROUP BY 1, 2 ORDER BY 1, 2
    """)


def price_regimes(con) -> list[dict]:
    """Share of time at negative or above-$300 prices, by region and financial year."""
    return _records(con, """
        SELECT region_code, fy,
               sum(interval_minutes) FILTER (WHERE price_aud_mwh < 0) * 1.0 / sum(interval_minutes) AS negative_time_share,
               sum(interval_minutes) FILTER (WHERE price_aud_mwh > 300) * 1.0 / sum(interval_minutes) AS above_300_time_share
        FROM m GROUP BY 1, 2 ORDER BY 1, 2
    """)


def negative_share_jul_oct(con) -> list[dict]:
    """Negative-price time in July to October only, to compare the part-year FY with the same months before."""
    return _records(con, """
        SELECT region_code, fy,
               sum(interval_minutes) FILTER (WHERE price_aud_mwh < 0) * 1.0 / sum(interval_minutes) AS negative_time_share
        FROM (SELECT *, month(date_key) AS mo FROM m) WHERE mo BETWEEN 7 AND 10 GROUP BY 1, 2 ORDER BY 1, 2
    """)


def compute(con) -> dict:
    _base(con)
    return {
        "golden_values": golden_values(con),
        "cost_concentration": cost_concentration(con),
        "cap_value": cap_value(con),
        "load_shift": load_shift(con),
        "battery_upper_bound": battery_upper_bound(con),
        "price_regimes": price_regimes(con),
        "negative_share_jul_oct": negative_share_jul_oct(con),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--star", default="data/star", type=Path)
    p.add_argument("--out", default="validation/golden_values.json", type=Path)
    a = p.parse_args()
    c = duckdb.connect()
    for t in ["fact_market", "dim_region", "dim_date", "dim_time"]:
        c.execute(f"CREATE TABLE {t} AS SELECT * FROM '{a.star / t}.parquet'")
    a.out.write_text(json.dumps(compute(c), indent=1, default=str))
    print("wrote", a.out)
