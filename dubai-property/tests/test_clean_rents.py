from pipeline.clean_rents import clean

HEADER = ("contract_id,line_number,contract_start_date,contract_end_date,annual_amount,actual_area,area_id,area_name_en,project_number,"
          "ejari_property_sub_type_en,ejari_property_type_en,tenant_type_en,no_of_prop,property_usage_en,contract_reg_type_en\n")
GOOD = "2026-01-01,2026-12-31,90000,80,1,A,10.00,1bed room+Hall,Flat,Person,1,Residential,New"


def rows(tmp_path, *lines):
    f = tmp_path / "r.csv"
    f.write_text(HEADER + "".join(f"C{i},1,{line}\n" for i, line in enumerate(lines)))
    return clean(str(f))


def test_keeps_a_good_contract_without_its_id(tmp_path):
    df, funnel = rows(tmp_path, GOOD)
    assert df.iloc[0]["rooms"] == "1 B/R" and df.iloc[0]["rent"] == 90000
    assert "contract_id" not in df.columns and funnel["one_line_per_contract"] == 1


def test_each_filter_removes_what_it_should(tmp_path):
    bad = {"residential": GOOD.replace("Residential", "Commercial"), "flat_or_villa": GOOD.replace("Flat", "Labor Camps"),
           "single_property": GOOD.replace(",1,Residential", ",8,Residential"), "about_a_year": GOOD.replace("2026-12-31", "2026-03-31"),
           "plausible_rent": GOOD.replace("90000", "900"), "plausible_size": GOOD.replace(",80,", ",1,"),
           "known_bedrooms": GOOD.replace("1bed room+Hall", "Office"), "new_contract": GOOD.replace(",New", ",Renew"),
           "in_period": GOOD.replace("2026-01-01", "2027-01-01").replace("2026-12-31", "2027-12-31")}
    for step, line in bad.items():
        df, funnel = rows(tmp_path, line)
        assert df.empty and funnel[step] == 0, step


def test_contract_with_two_lines_counts_once(tmp_path):
    f = tmp_path / "r.csv"
    f.write_text(HEADER + f"C1,1,{GOOD}\nC1,2,{GOOD}\n")
    df, funnel = clean(str(f))
    assert len(df) == 1 and funnel["new_contract"] == 2 and funnel["one_line_per_contract"] == 1
