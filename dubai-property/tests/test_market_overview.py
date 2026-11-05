import pandas as pd
from pipeline.market_overview import bands_around_line, quarterly_crowding, rents_by_year, sales_by_year


def sales():
    return pd.DataFrame({
        "year": ["2014", "2025", "2025", "2025", "2025", "2025", "2025"],
        "date": ["2014-01-01", "2025-01-10", "2025-02-10", "2025-03-10", "2025-03-11", "2025-03-12", "2025-04-10"],
        "value": [2_000_000, 1_990_000, 2_000_000, 2_010_000, 1_510_000, 1_490_000, 2_000_000],
    })


def test_sales_start_in_2015():
    assert sales_by_year(sales()) == [{"year": "2025", "sales": 6}]


def test_bands_put_the_line_in_the_band_above():
    bands = {b["from_aed"]: b["sales"] for b in bands_around_line(sales())}
    assert bands[1_975_000] == 1 and bands[2_000_000] == 3


def test_crowding_compares_above_with_below():
    q1, q2 = quarterly_crowding(sales())
    assert q1 == {"quarter": "2025 Q1", "at_2m": 2.0, "comparison": 1.0}
    assert q2 == {"quarter": "2025 Q2", "at_2m": None, "comparison": None}


def test_rents_keep_only_single_residential_contracts(tmp_path):
    f = tmp_path / "r.csv"
    f.write_text("contract_start_date,annual_amount,no_of_prop,property_usage_en,ejari_property_type_en\n"
                 "2025-01-01,60000,1,Residential,Flat\n2025-01-02,900000,8,Residential,Flat\n2025-01-03,70000,1,Commercial,Flat\n")
    assert rents_by_year(str(f)) == [{"year": "2025", "type": "Flat", "contracts": 1, "median_aed": 60000}]
