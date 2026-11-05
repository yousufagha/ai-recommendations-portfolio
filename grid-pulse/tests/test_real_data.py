"""Integrity checks on the full AEMO build. Skipped in CI, where raw data is absent."""
from pathlib import Path

import duckdb
import pytest

FACT = Path("data/star/fact_market.parquet")
pytestmark = pytest.mark.skipif(not FACT.exists(), reason="full data not built")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect()
    c.execute(f"CREATE VIEW f AS SELECT * FROM '{FACT}'")
    return c


def test_no_duplicate_intervals(con):
    assert con.execute(
        "SELECT count(*) FROM (SELECT 1 FROM f GROUP BY region_code, interval_end HAVING count(*) > 1)"
    ).fetchone()[0] == 0


def test_no_gaps_at_declared_interval_length(con):
    bad = con.execute("""
        WITH g AS (
            SELECT interval_minutes,
                   date_diff('minute', lag(interval_end) OVER (PARTITION BY region_code ORDER BY interval_end), interval_end) AS gap
            FROM f
        )
        SELECT count(*) FROM g WHERE gap <> interval_minutes
    """).fetchone()[0]
    assert bad == 0


@pytest.mark.parametrize("month,expected", [("2021-09", 1440), ("2021-10", 8928)])
def test_interval_counts_either_side_of_boundary(con, month, expected):
    assert con.execute(
        "SELECT count(*) FROM f WHERE region_code = 'VIC1' AND strftime(interval_start, '%Y-%m') = ?", [month]
    ).fetchone()[0] == expected
