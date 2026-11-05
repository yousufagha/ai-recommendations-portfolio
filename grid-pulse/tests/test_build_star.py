import datetime as dt
from pathlib import Path

import pytest

from pipeline.build_star import build

FIXTURE = str(Path(__file__).parent / "fixtures" / "PRICE_AND_DEMAND_boundary_VIC1.csv")


@pytest.fixture()
def con(tmp_path):
    return build(FIXTURE, tmp_path)


def rows(con):
    return con.execute(
        "SELECT interval_end, interval_start, date_key, time_key, interval_minutes, energy_mwh, turnover_aud "
        "FROM fact_market ORDER BY interval_end"
    ).fetchall()


def test_midnight_interval_belongs_to_previous_day(con):
    r = rows(con)[1]
    assert r[0] == dt.datetime(2021, 10, 1, 0, 0)
    assert r[2] == dt.date(2021, 9, 30)
    assert r[3] == 23 * 60 + 30


def test_interval_length_switches_after_boundary(con):
    assert [r[4] for r in rows(con)] == [30, 30, 5, 5]


def test_first_five_minute_interval_starts_at_midnight(con):
    r = rows(con)[2]
    assert r[1] == dt.datetime(2021, 10, 1, 0, 0)
    assert r[2] == dt.date(2021, 10, 1)
    assert r[3] == 0


def test_energy_uses_interval_length(con):
    assert [round(r[5], 4) for r in rows(con)] == [500.0, 500.0, 166.6667, 166.6667]


def test_energy_weighted_price_differs_from_naive_average(con):
    weighted, naive = con.execute(
        "SELECT sum(turnover_aud) / sum(energy_mwh), avg(price_aud_mwh) FROM fact_market"
    ).fetchone()
    assert round(naive, 2) == 60.0
    # (500*100 + 500*100 + 166.67*-10 + 166.67*50) / 1333.33
    assert weighted == pytest.approx(80.0)


def test_every_fact_key_resolves_to_dimensions(con):
    orphans = con.execute("""
        SELECT count(*) FROM fact_market f
        LEFT JOIN dim_date d USING (date_key)
        LEFT JOIN dim_time t USING (time_key)
        LEFT JOIN dim_region r USING (region_code)
        WHERE d.date_key IS NULL OR t.time_key IS NULL OR r.region_code IS NULL
    """).fetchone()[0]
    assert orphans == 0


def test_dim_time_has_one_row_per_five_minutes(con):
    assert con.execute("SELECT count(*), count(DISTINCT time_key) FROM dim_time").fetchone() == (288, 288)


def test_financial_year_is_july_to_june(con):
    fy = dict(con.execute(
        "SELECT date_key, financial_year FROM dim_date WHERE date_key IN ('2021-06-30', '2021-07-01')"
    ).fetchall())
    assert fy[dt.date(2021, 6, 30)] == 2021
    assert fy[dt.date(2021, 7, 1)] == 2022
