import json
import re

from pipeline.build_site import ROOT, chart_data, figures, load_results, render, short_aed

PAGE = ROOT / "docs" / "index.html"
TEMPLATE = ROOT / "dubai-property" / "site" / "index.template.html"


def test_published_page_is_the_built_page():
    assert PAGE.read_text() == render(TEMPLATE.read_text(), load_results())


def test_price_labels_keep_their_precision():
    assert [short_aed(v) for v in (1_975_000, 2_000_000, 2_025_000, 1_800_000)] == ["AED 1.975M", "AED 2.0M", "AED 2.025M", "AED 1.8M"]


def test_chart_data_on_the_page_matches_the_results():
    results = load_results()
    embedded = re.search(r'<script id="chart-data" type="application/json">(.*?)</script>', PAGE.read_text(), re.DOTALL).group(1)
    assert json.loads(embedded) == chart_data(results)


def test_every_written_claim_holds_in_the_results():
    results = load_results()
    f, data = figures(results), chart_data(results)
    assert f["quarters_above"] == f["quarters_total"], "the page says the pattern held in every quarter since Q2 2022"
    assert max(data["bands"], key=lambda b: b["value"])["highlight"], "the page says AED 2M was the most popular nearby band"
    assert data["yields"][0]["highlight"] and [y["value"] for y in data["yields"]] == sorted((y["value"] for y in data["yields"]), reverse=True)
    tier = [y for y in data["yields"] if y["highlight"]]
    assert len(tier) >= 2 and round(tier[-1]["value"]) == 6, "the page says the top options run from about 6%"
    assert int(f["rent_gap"].replace(",", "")) == max(y["rent"] for y in data["yields"]) - min(y["rent"] for y in data["yields"])
    tested = [x for x in results["backtest"]["rounds"] if x["tested"]]
    assert f["verdict"] == "not shown", "the page and dashboard say no total-return edge is claimed"
    assert f["rounds_tested"] == f["rounds_more_rent"] == "4", "STORY.md and the Tableau guide say 4 of 4 rounds"
    assert (f["rent_aed_low"], f["rent_aed_high"]) == ("50,000", "73,000"), "STORY.md and the Tableau guide quote these dirham figures"
    assert all(x["picks_realised_yield_pct"] > x["others_realised_yield_pct"] for x in tested), "the page says picks earned more rent in every round"
    rent = results["backtest"]["rent_only_permutation_added_after_seeing_results"]
    assert rent["share_of_random_at_least_as_good"] == 0, "the page says the rent gap beat all random picks"
    p = results["backtest"]["permutation"]
    assert (p["plan"]["observed_points"] > p["plan"]["random_95th_points"]) != (p["centred"]["observed_points"] > p["centred"]["random_95th_points"]), "the page says one measure of two"
    assert f["wider_behind"] == "3", "the page says the picks trailed all ready flats on total return in 3 of 4 rounds"
    assert float(f["crowd_before"]) < float(f["crowd_after"]), "the page says the crowding at the line grew"
    assert (f["yield_low"], f["yield_high"]) == ("5.2", "6.4"), "the page quotes the yield range of the ranked options"
    assert (f["rent_aed_2m_low"], f["rent_aed_2m_high"]) == ("10,000", "15,000"), "the page restates the rent gap on AED 2 million"
    assert [round(a - b, 2) for a, b in zip(data["backtest"]["series"][0]["values"], data["backtest"]["series"][1]["values"])] == [0.5, 0.6, 0.73, 0.58], "the chart labels show these gaps"
    assert data["shift"][0]["label"] == data["tail"][0]["label"] == "South Australia"
    highlight = next(s for s in data["steps"] if s["highlight"])
    assert any(abs(s["value"]) >= abs(highlight["value"]) for s in data["steps"] if not s["highlight"]), "no clear cost relies on this"


def test_search_and_trust_lines_stay_on_the_page():
    text = PAGE.read_text()
    for needed in ("google-site-verification", 'rel="canonical"', "application/ld+json", "not endorsed by or affiliated", "data-catalog.json"):
        assert needed in text


def test_local_data_links_exist():
    for path in set(re.findall(r"github\.com/yousufagha/ai-recommendations-portfolio/(?:blob|tree)/main/([^\"#]+)", PAGE.read_text())):
        assert (ROOT / path).exists(), path


def test_page_has_no_em_dash_or_unfilled_placeholder():
    text = PAGE.read_text()
    assert "\u2014" not in text and "{{" not in text
