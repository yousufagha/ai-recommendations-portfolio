import datetime as dt

import duckdb
import pytest
from pipeline.build_star import build_dimensions
from pipeline.insights import EFFICIENCY, compute


def fact(prices_by_slot):
    """One 2023 financial-year-spanning region: one day of 5-minute rows per half-hour slot price."""
    con = duckdb.connect()
    con.execute("""CREATE TABLE fact_market (region_code VARCHAR, interval_end TIMESTAMP, interval_start TIMESTAMP,
        date_key DATE, time_key INTEGER, interval_minutes INTEGER, demand_mw DOUBLE, price_aud_mwh DOUBLE,
        energy_mwh DOUBLE, turnover_aud DOUBLE)""")
    day = dt.date(2023, 6, 30)  # a Friday, and the last day of FY2023, so the year counts as complete
    start = dt.datetime.combine(day, dt.time())
    for minute in range(0, 1440, 5):
        price = prices_by_slot(minute)
        s = start + dt.timedelta(minutes=minute)
        energy = 1200 * 5 / 60
        con.execute("INSERT INTO fact_market VALUES ('VIC1', ?, ?, ?, ?, 5, 1200, ?, ?, ?)",
                    [s + dt.timedelta(minutes=5), s, day, minute, price, energy, energy * price])
    build_dimensions(con)
    return con


def test_cap_value_is_load_weighted_excess_over_strike():
    con = fact(lambda m: 1000 if m < 60 else 100)
    r = compute(con)["cap_value"][0]
    # 1 hour in 24 at $1000: excess over 300 is 700, over 24 hours of flat load
    assert r["cap_300_aud_mwh"] == pytest.approx(700 / 24, abs=1e-3)
    assert r["cap_500_aud_mwh"] == pytest.approx(500 / 24, abs=1e-3)


def test_load_shift_uses_evening_minus_solar():
    def price(m):
        return 200 if 960 <= m < 1260 else 20 if 600 <= m < 960 else 50
    r = compute(fact(price))["load_shift"][0]
    assert r["spread_aud_mwh"] == pytest.approx(180)
    assert r["saving_aud_per_mw_year"] == pytest.approx(180 * 4 * 1)


def test_battery_buys_cheapest_two_hours_and_sells_dearest_two():
    def price(m):
        return 10 if m < 120 else 300 if 1080 <= m < 1200 else 50
    r = compute(fact(price))["battery_upper_bound"][0]
    assert r["gross_aud_per_mw_year"] == pytest.approx(2 * 300 - 2 * 10 / EFFICIENCY, abs=1e-3)


def test_incomplete_financial_year_is_excluded():
    con = fact(lambda m: 100)
    con.execute("UPDATE fact_market SET date_key = DATE '2023-06-29'")
    assert compute(con)["cap_value"] == []


def test_golden_values_report_both_price_measures():
    con = fact(lambda m: 100)
    g = compute(con)["golden_values"][0]
    assert g["energy_weighted_price"] == pytest.approx(100)
    assert g["time_weighted_price"] == pytest.approx(100)
    assert g["intervals"] == 288
