"""Build the Grid Pulse star schema from AEMO price and demand CSVs.

AEMO timestamps are interval-ending in market time (UTC+10, no daylight saving).
Settlement moved from 30-minute to 5-minute intervals: the last 30-minute row ends at
2021-10-01 00:00. Energy, not row counts, is the basis of every aggregate.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

LAST_30_MIN_TS = "2021-10-01 00:00:00"

REGIONS = [
    ("NSW1", "New South Wales", "NSW", 1),
    ("QLD1", "Queensland", "QLD", 2),
    ("SA1", "South Australia", "SA", 3),
    ("TAS1", "Tasmania", "TAS", 4),
    ("VIC1", "Victoria", "VIC", 5),
]


def load_market(con: duckdb.DuckDBPyConnection, raw_glob: str) -> None:
    con.execute(f"""
        CREATE OR REPLACE TABLE fact_market AS
        WITH src AS (
            SELECT REGION AS region_code,
                   strptime(SETTLEMENTDATE, '%Y/%m/%d %H:%M:%S') AS interval_end,
                   CAST(TOTALDEMAND AS DOUBLE) AS demand_mw,
                   CAST(RRP AS DOUBLE) AS price_aud_mwh
            FROM read_csv('{raw_glob}', header = true, all_varchar = true)
        ),
        timed AS (
            SELECT *, CASE WHEN interval_end <= TIMESTAMP '{LAST_30_MIN_TS}' THEN 30 ELSE 5 END AS interval_minutes
            FROM src
        ),
        started AS (
            SELECT *, interval_end - to_minutes(interval_minutes) AS interval_start FROM timed
        )
        SELECT region_code,
               interval_end,
               interval_start,
               CAST(interval_start AS DATE) AS date_key,
               CAST(hour(interval_start) * 60 + minute(interval_start) AS INTEGER) AS time_key,
               CAST(interval_minutes AS INTEGER) AS interval_minutes,
               demand_mw,
               price_aud_mwh,
               demand_mw * interval_minutes / 60.0 AS energy_mwh,
               demand_mw * interval_minutes / 60.0 * price_aud_mwh AS turnover_aud
        FROM started
        ORDER BY region_code, interval_end
    """)


def build_dimensions(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("CREATE OR REPLACE TABLE dim_region (region_code VARCHAR, region_name VARCHAR, state VARCHAR, sort_order INTEGER)")
    con.executemany("INSERT INTO dim_region VALUES (?, ?, ?, ?)", REGIONS)

    con.execute("""
        CREATE OR REPLACE TABLE dim_date AS
        WITH bounds AS (
            SELECT date_trunc('year', min(date_key)) AS lo,
                   date_trunc('year', max(date_key)) + INTERVAL 1 YEAR - INTERVAL 1 DAY AS hi
            FROM fact_market
        ),
        d AS (SELECT CAST(unnest(generate_series(lo, hi, INTERVAL 1 DAY)) AS DATE) AS date_key FROM bounds)
        SELECT date_key,
               CAST(year(date_key) AS INTEGER) AS year,
               CAST(quarter(date_key) AS INTEGER) AS quarter,
               CAST(month(date_key) AS INTEGER) AS month_number,
               strftime(date_key, '%b') AS month_name,
               CAST(date_trunc('month', date_key) AS DATE) AS month_start,
               CAST(year(date_key) + CASE WHEN month(date_key) >= 7 THEN 1 ELSE 0 END AS INTEGER) AS financial_year,
               CAST(isodow(date_key) AS INTEGER) AS day_of_week_number,
               strftime(date_key, '%a') AS day_of_week,
               isodow(date_key) >= 6 AS is_weekend,
               CASE WHEN month(date_key) IN (12, 1, 2) THEN 'Summer'
                    WHEN month(date_key) IN (3, 4, 5) THEN 'Autumn'
                    WHEN month(date_key) IN (6, 7, 8) THEN 'Winter'
                    ELSE 'Spring' END AS season
        FROM d
        ORDER BY date_key
    """)

    con.execute("""
        CREATE OR REPLACE TABLE dim_time AS
        WITH t AS (SELECT CAST(unnest(generate_series(0, 1435, 5)) AS INTEGER) AS time_key)
        SELECT time_key,
               CAST(time_key // 60 AS INTEGER) AS hour,
               printf('%02d:%02d', time_key // 60, time_key % 60) AS time_label,
               CASE WHEN time_key < 360 THEN 'Overnight'
                    WHEN time_key < 600 THEN 'Morning'
                    WHEN time_key < 960 THEN 'Solar'
                    WHEN time_key < 1260 THEN 'Evening peak'
                    ELSE 'Late' END AS day_part,
               CASE WHEN time_key < 360 THEN 1 WHEN time_key < 600 THEN 2 WHEN time_key < 960 THEN 3
                    WHEN time_key < 1260 THEN 4 ELSE 5 END AS day_part_order
        FROM t
        ORDER BY time_key
    """)


def export(con: duckdb.DuckDBPyConnection, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    for table in ["fact_market", "dim_region", "dim_date", "dim_time"]:
        con.execute(f"COPY {table} TO '{out / table}.parquet' (FORMAT parquet, COMPRESSION zstd)")


def build(raw_glob: str, out: Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    load_market(con, raw_glob)
    build_dimensions(con)
    export(con, out)
    return con


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--raw", default="data/raw/aemo/*.csv")
    p.add_argument("--out", default="data/star", type=Path)
    a = p.parse_args()
    c = build(a.raw, a.out)
    print(c.execute("SELECT count(*), min(interval_start), max(interval_end) FROM fact_market").fetchone())
