"""Write the tested results as flat files for the Tableau Public dashboard. No new analysis happens here."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {"ready_ranked": "Ready, ranked", "ready_indicative": "Ready, indicative", "off_plan_indicative": "Off-plan, indicative", "villas_not_ranked": "Villa, not ranked"}
BEDROOMS = {"Studio": "Studio", "1 B/R": "1-bed", "2 B/R": "2-bed", "3 B/R": "3-bed", "4 B/R": "4-bed"}


def options(yields: dict) -> list[dict]:
    rows = []
    for key, group in GROUPS.items():
        for x in yields[key]:
            rows.append({"group": group, "home": f"{x['area']}, {BEDROOMS.get(x['rooms'], x['rooms'])}", "area": x["area"], "bedrooms": BEDROOMS.get(x["rooms"], x["rooms"]),
                         "type": x["type"], "sales": x["sales"], "price_aed": x["price_aed"], "size_sqm": x["size_sqm"], "rent_aed": x["rent_aed"],
                         "gross_yield_pct": x["yield_pct"], "yield_low_pct": x["low_pct"], "yield_high_pct": x["high_pct"], "all_price_yield_pct": x["all_price_yield_pct"],
                         "project_evidence_share": x["project_share"], "price_tier_evidence_share": x["tier_share"], "area_evidence_share": x["area_share"],
                         "top_tier": bool(x.get("top_tier", False))})
    return rows


def backtest_rounds(backtest: dict) -> list[dict]:
    rows = []
    for x in backtest["rounds"]:
        s, hold = x["sensitivity"], x["hold_to_data_cut"] or {}
        rows.append({"decision": x["decision"], "tested": x["tested"], "options": x["options"], "picks_rent_pct": x["picks_realised_yield_pct"], "others_rent_pct": x["others_realised_yield_pct"],
                     "picks_price_change_pct": x["picks_price_change_pct"], "others_price_change_pct": x["others_price_change_pct"],
                     "total_gap_first_price_measure": x["excess_plan_points"], "total_gap_second_price_measure": x["excess_centred_points"], "total_gap_well_measured_only": s["well_measured_options_only"],
                     "total_gap_against_all_ready_flats": x["picks_minus_wider_market_points"], "hold_years": hold.get("years"), "hold_picks_total_pct": hold.get("picks_total_pct"), "hold_others_total_pct": hold.get("others_total_pct")})
    return rows


def backtest_picks(backtest: dict) -> list[dict]:
    return [{"decision": x["decision"], "tested": x["tested"], "rank": i + 1, "home": home} for x in backtest["rounds"] for i, home in enumerate(x["picks"])]


def price_steps(lines: dict) -> list[dict]:
    rows = [x for x in lines["by_line"] if x["period"] == "from_q2_2022" and x["stage"] == "all"] + [x for x in lines["robustness"] if x["check"] == "nearby_price"]
    return [{"price_aed": x["line"], "step_pct": x["step_pct"], "low_pct": x["low_pct"], "high_pct": x["high_pct"], "visa_line": x["line"] == 2_000_000} for x in sorted(rows, key=lambda r: r["line"])]


def tables(root: Path = ROOT) -> dict[str, list[dict]]:
    d = root / "validation"
    overview, lines = json.loads((d / "market_overview.json").read_text()), json.loads((d / "value_at_line.json").read_text())
    yields, backtest = json.loads((d / "rent_yields.json").read_text()), json.loads((d / "backtest.json").read_text())
    crowd = [{"quarter": x["quarter"], "series": name, "sales_above_per_sale_below": x[key]} for x in overview["quarterly_crowding"] for name, key in (("AED 2M", "at_2m"), ("AED 1.5M, 2.5M and 3M", "comparison"))]
    return {"options": options(yields), "backtest_rounds": backtest_rounds(backtest), "backtest_picks": backtest_picks(backtest), "price_steps": price_steps(lines),
            "sales_by_year": overview["sales_by_year"], "rents_by_year": overview["rents_by_year"], "sales_bands_2025": overview["bands_2025"], "crowding_by_quarter": crowd}


def write(out: Path, root: Path = ROOT) -> dict[str, int]:
    out.mkdir(parents=True, exist_ok=True)
    counts = {}
    for name, rows in tables(root).items():
        with (out / f"{name}.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        counts[name] = len(rows)
    return counts


if __name__ == "__main__":
    print(write(ROOT / "tableau"))
