"""Build the landing page from the results files, so every figure on it traces to a tested result."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGIONS = {"NSW1": "New South Wales", "QLD1": "Queensland", "SA1": "South Australia", "TAS1": "Tasmania", "VIC1": "Victoria"}


def table(caption: str, headers: list[str], rows: list[list]) -> str:
    head = "".join(f'<th scope="col">{html.escape(h)}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return (f"<details><summary>Show the data</summary><div class=\"scroll\"><table><caption>{html.escape(caption)}</caption>"
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></details>")


def short_aed(value: float) -> str:
    digits = f"{value / 1e6:.3f}".rstrip("0")
    return f"AED {digits}0M" if digits.endswith(".") else f"AED {digits}M"


def load_results(root: Path = ROOT) -> dict:
    d = root / "dubai-property" / "validation"
    return {"overview": json.loads((d / "market_overview.json").read_text()),
            "lines": json.loads((d / "value_at_line.json").read_text()),
            "yields": json.loads((d / "rent_yields.json").read_text()),
            "backtest": json.loads((d / "backtest.json").read_text()),
            "grid": json.loads((root / "grid-pulse" / "validation" / "golden_values.json").read_text())}


def chart_data(r: dict) -> dict:
    o, lines = r["overview"], r["lines"]
    rents = {t: [x for x in o["rents_by_year"] if x["type"] == t] for t in ("Flat", "Villa")}
    main = [x for x in lines["by_line"] if x["period"] == "from_q2_2022" and x["stage"] == "all"]
    near = [x for x in lines["robustness"] if x["check"] == "nearby_price"]
    steps = sorted(main + near, key=lambda x: x["line"])
    fy = lambda key: {x["region_code"]: x for x in r["grid"][key] if x["fy"] == 2026}
    order = sorted(REGIONS, key=lambda c: -fy("load_shift")[c]["saving_aud_per_mw_year"])
    tested = [x for x in r["backtest"]["rounds"] if x["tested"]]
    bedrooms = {"1 B/R": "1-bed", "2 B/R": "2-bed", "3 B/R": "3-bed"}
    return {
        "yields": [{"label": f"{x['area']}, {bedrooms.get(x['rooms'], x['rooms'])}", "value": x["yield_pct"], "rent": x["rent_aed"],
                    "highlight": x["top_tier"]} for x in r["yields"]["ready_ranked"]],
        "backtest": {"x": [f"Nov {x['decision'][:4]}" for x in tested],
                     "series": [{"name": "Picked homes", "values": [x["picks_realised_yield_pct"] for x in tested]},
                                {"name": "Other ranked homes", "values": [x["others_realised_yield_pct"] for x in tested]}]},
        "backtest_rows": [[f"Nov {x['decision'][:4]}", x["picks_realised_yield_pct"], x["others_realised_yield_pct"], x["excess_plan_points"], x["excess_centred_points"],
                           x["sensitivity"]["well_measured_options_only"], x["picks_minus_wider_market_points"]] for x in tested],
        "sales": [{"label": x["year"], "value": x["sales"], "partial": x["year"] == "2026"} for x in o["sales_by_year"]],
        "rents": {"x": [x["year"] for x in rents["Flat"]],
                  "series": [{"name": f"{t}s", "values": [x["median_aed"] for x in rents[t]]} for t in ("Villa", "Flat")]},
        "bands": [{"label": short_aed(x["from_aed"]), "value": x["sales"], "highlight": x["from_aed"] == 2_000_000} for x in o["bands_2025"]],
        "crowding": {"x": [x["quarter"] for x in o["quarterly_crowding"]],
                     "series": [{"name": "AED 2M", "values": [x["at_2m"] for x in o["quarterly_crowding"]]},
                                {"name": "AED 1.5M, 2.5M and 3M", "values": [x["comparison"] for x in o["quarterly_crowding"]]}]},
        "steps": [{"label": short_aed(x["line"]), "value": x["step_pct"], "low": x["low_pct"], "high": x["high_pct"],
                   "highlight": x["line"] == 2_000_000} for x in steps],
        "shift": [{"label": REGIONS[c], "value": round(fy("load_shift")[c]["saving_aud_per_mw_year"])} for c in order],
        "tail": [{"label": REGIONS[c], "value": round(fy("cost_concentration")[c]["top_1pct_cost_share"] * 100, 1)}
                 for c in sorted(REGIONS, key=lambda c: -fy("cost_concentration")[c]["top_1pct_cost_share"])],
    }


def figures(r: dict) -> dict:
    o, lines = r["overview"], r["lines"]
    sales = {x["year"]: x["sales"] for x in o["sales_by_year"]}
    flat = {x["year"]: x["median_aed"] for x in o["rents_by_year"] if x["type"] == "Flat"}
    crowd = {(x["period"], x["line"]): x for x in lines["crowding"]}
    step = next(x for x in lines["by_line"] if x["period"] == "from_q2_2022" and x["stage"] == "all" and x["line"] == 2_000_000)
    quarters = [x for x in o["quarterly_crowding"] if x["quarter"] >= "2022 Q2"]
    bands = {x["from_aed"]: x["sales"] for x in o["bands_2025"]}
    ranked = r["yields"]["ready_ranked"]
    rents = [x["rent_aed"] for x in ranked]
    evidence = r["yields"]["evidence"]
    near = sum(x["sales"] for x in evidence)
    off_plan = sum(x["sales"] for x in evidence if x["stage"] == "off_plan")
    held_out = r["yields"]["checks"]["leave_project_out"]
    b = r["backtest"]
    tested = [x for x in b["rounds"] if x["tested"]]
    gaps = [x["picks_realised_yield_pct"] - x["others_realised_yield_pct"] for x in tested]
    wins = b["verdict"]["rounds_ahead_on_both_windows"]
    return {
        "rounds_tested": str(len(tested)), "rounds_more_rent": str(sum(g > 0 for g in gaps)), "total_rounds_ahead": str(wins),
        "rent_gap_low": f"{min(gaps):.1f}", "rent_gap_high": f"{max(gaps):.1f}",
        "rent_aed_low": f"{round(min(gaps) / 100 * 10_000_000, -3):,.0f}", "rent_aed_high": f"{round(max(gaps) / 100 * 10_000_000, -3):,.0f}",
        "rent_aed_2m_low": f"{round(min(gaps) / 100 * 2_000_000, -3):,.0f}", "rent_aed_2m_high": f"{round(max(gaps) / 100 * 2_000_000, -3):,.0f}",
        "random_draws": f"{5000:,}", "verdict": b["verdict"]["label"],
        "sum_plan": f"{b['permutation']['plan']['observed_points']:.1f}", "sum_centred": f"{b['permutation']['centred']['observed_points']:.1f}",
        "wider_behind": str(sum(x["picks_minus_wider_market_points"] < 0 for x in tested)),
        "ranked_count": str(len(ranked)), "top_tier_count": str(sum(x["top_tier"] for x in ranked)),
        "yield_low": f"{ranked[-1]['yield_pct']:.1f}", "yield_high": f"{ranked[0]['yield_pct']:.1f}",
        "rent_low": f"{min(rents):,}", "rent_high": f"{max(rents):,}", "rent_gap": f"{max(rents) - min(rents):,}",
        "yield_error": f"{held_out['median_abs_yield_points']:.2f}", "off_plan_share": f"{off_plan / near:.0%}",
        "rank_correlation": f"{r['yields']['checks']['last_year_rents']['spearman']:.2f}",
        "sales_2019": f"{sales['2019']:,}", "sales_2025": f"{sales['2025']:,}", "sales_multiple": f"{sales['2025'] / sales['2019']:.1f}",
        "flat_2021": f"{flat['2021']:,}", "flat_2026": f"{flat['2026']:,}", "flat_growth": f"{flat['2026'] / flat['2021'] - 1:.0%}",
        "crowd_before": f"{crowd[('before_2022', 2_000_000)]['ratio']:.2f}", "crowd_after": f"{crowd[('from_q2_2022', 2_000_000)]['ratio']:.2f}",
        "quarters_above": str(sum(x["at_2m"] > x["comparison"] for x in quarters)), "quarters_total": str(len(quarters)),
        "band_2m": f"{bands[2_000_000]:,}", "band_below": f"{bands[1_975_000]:,}",
        "step_aed": f"{round(step['step_aed'], -3):,}", "step_low": f"{round(step['low_aed'], -3):,}", "step_high": f"{round(step['high_aed'], -3):,}",
        "step_pct": f"{step['step_pct']:.1f}",
    }


def tables(data: dict) -> dict:
    series = lambda c: [[x] + [s["values"][i] for s in c["series"]] for i, x in enumerate(c["x"])]
    return {
        "table_backtest": table("Each round: yearly rent as a percent of price, and gaps in points", ["Decision", "Picked homes' rent", "Others' rent", "Total gap, first price measure", "Total gap, second price measure",
                                "Total gap, well-measured options only", "Total gap against all ready flats"], data["backtest_rows"]),
        "table_yields": table("Estimated gross yield and yearly rent, ready flats priced at AED 2M to 2.2M", ["Home", "Gross yield, percent", "Rent a year, AED"],
                              [[x["label"], x["value"], f"{x['rent']:,}"] for x in data["yields"]]),
        "table_sales": table("Residential flat and villa sales by year", ["Year", "Sales"], [[x["label"], f"{x['value']:,}"] for x in data["sales"]]),
        "table_rents": table("Median yearly rent in dirhams", ["Year"] + [s["name"] for s in data["rents"]["series"]], series(data["rents"])),
        "table_bands": table("2025 sales by AED 25,000 price band", ["Band from", "Sales"], [[x["label"], f"{x['value']:,}"] for x in data["bands"]]),
        "table_crowding": table("Sales just above a price for each sale just below it", ["Quarter"] + [s["name"] for s in data["crowding"]["series"]], series(data["crowding"])),
        "table_steps": table("Step in price for a comparable home, from Q2 2022, percent", ["Price", "Step", "Low", "High"],
                             [[x["label"], x["value"], x["low"], x["high"]] for x in data["steps"]]),
        "table_shift": table("Yearly value of moving 1 MW, FY2026, Australian dollars", ["Region", "Value"], [[x["label"], f"{x['value']:,}"] for x in data["shift"]]),
        "table_tail": table("Share of wholesale cost in the dearest 1% of intervals, FY2026, percent", ["Region", "Share"], [[x["label"], x["value"]] for x in data["tail"]]),
    }


def render(template: str, r: dict) -> str:
    data = chart_data(r)
    page = template.replace("{{chart_data}}", json.dumps(data, separators=(",", ":")))
    for key, value in {**figures(r), **tables(data)}.items():
        page = page.replace("{{" + key + "}}", value)
    if "{{" in page:
        raise ValueError("A placeholder was left unfilled")
    return page


if __name__ == "__main__":
    template = (ROOT / "dubai-property" / "site" / "index.template.html").read_text()
    (ROOT / "docs" / "index.html").write_text(render(template, load_results()))
    print("wrote docs/index.html")
