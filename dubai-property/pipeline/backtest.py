"""Would the AED 2M rent ranking have picked better homes than other AED 2M homes, knowing only what was known then?

Each year's picks use only the 12 months before the decision. They are then scored on what happened next: new rents
actually agreed and a pooled price change. With only four tested rounds the test has little power, so "not shown"
is the likely outcome even if the method has a real edge of 1 to 2 points a year.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from pipeline.clean_rents import DATA_CUT, clean
from pipeline.rent_yields import PRICE_BAND, estimate_rents, fit_beta, load_sales, options, rank_ready

ROUNDS = ("2021-11-03", "2022-11-03", "2023-11-03", "2024-11-03", "2025-11-03")
NO_TEST = {"2021-11-03"}
AMOUNT = 10_000_000
TOP = 5
FEE_PCT = 4.0
SERVICE_AED_PER_SQM = 200
INDEX_TOLERANCE = 5.0
PERMUTATIONS = 5000
MIN_MATCHED = 100
OPTION = ["area_id", "rooms"]
WINDOWS = {"plan": ((-6, 0), (6, 12)), "centred": ((-3, 3), (9, 15))}


def shift(date: str, months: int, days: int = 0) -> str:
    return (pd.Timestamp(date) + pd.DateOffset(months=months, days=days)).strftime("%Y-%m-%d")


def window(date: str, start: int, end: int) -> tuple[str, str]:
    return shift(date, start, 1), shift(date, end)


def between(frame: pd.DataFrame, column: str, span: tuple[str, str]) -> pd.DataFrame:
    return frame[frame[column].between(*span)]


def decide(date: str, rents: pd.DataFrame, sales: pd.DataFrame, embargo_days: int = 0) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    """Options, ranked by estimated yield, using only records dated up to the decision."""
    span = (shift(date, -12, 1), shift(date, 0, -embargo_days))
    r, s = between(rents, "start", span), between(sales, "date", span)
    near = s[s["value"].between(*PRICE_BAND) & (s["type"] == "Flat")]
    if near.empty:
        return pd.DataFrame(), near, 0.0
    beta = fit_beta(r, s)
    table = options(estimate_rents(near, r, s, beta), r, s)
    return table, near, beta


def price_changes(sales: pd.DataFrame, base: tuple[str, str], end: tuple[str, str], drop_near: bool = False) -> pd.DataFrame:
    """Percent log change in price per sqm for each option: project and bedroom effects, log size, option by period."""
    d = sales[(sales["type"] == "Flat") & sales["project"].notna()]
    if drop_near:
        d = d[~d["value"].between(*PRICE_BAND)]
    d = pd.concat([between(d, "date", base).assign(post=0.0), between(d, "date", end).assign(post=1.0)], ignore_index=True)
    d["cell"] = d["project"] + "|" + d["rooms"]
    both = d.groupby("cell")["post"].transform("nunique") == 2
    d = d[both].copy()
    if d.empty:
        return pd.DataFrame(columns=[*OPTION, "change_pct", "matched"])
    codes, labels = pd.factorize(d["area_id"] + "|" + d["rooms"])
    x = np.zeros((len(d), len(labels) + 1))
    x[np.arange(len(d)), codes] = d["post"].to_numpy()
    x[:, -1] = np.log(d["size"].to_numpy())
    y = np.log(d["value"] / d["size"]).to_numpy()
    cells = pd.factorize(d["cell"])[0]
    counts = np.bincount(cells)
    y = y - (np.bincount(cells, y) / counts)[cells]
    for i in range(x.shape[1]):
        x[:, i] -= (np.bincount(cells, x[:, i]) / counts)[cells]
    coef = np.linalg.lstsq(x, y, rcond=None)[0][:-1]
    split = [label.split("|", 1) for label in labels]
    return pd.DataFrame({"area_id": [a for a, _ in split], "rooms": [b for _, b in split], "change_pct": coef * 100,
                         "matched": np.bincount(codes)})


def realised_rents(table: pd.DataFrame, near: pd.DataFrame, span: tuple[str, str], rents: pd.DataFrame, sales: pd.DataFrame, beta: float) -> pd.Series:
    """The same estimator, applied to contracts agreed after the decision."""
    r, s = between(rents, "start", span), between(sales, "date", span)
    wanted = near.merge(table[["area_id", "rooms"]].drop_duplicates(), on=OPTION)
    est = estimate_rents(wanted, r, s, beta)
    return est[est["level"] != "none"].groupby(OPTION)["rent"].median()


def score(table: pd.DataFrame, realised: pd.Series, change: pd.DataFrame) -> pd.DataFrame:
    """Realised yield plus price change. Options without a price change cannot be scored."""
    d = table.merge(change, on=OPTION, how="left").join(realised.rename("realised_rent"), on=OPTION)
    d["realised_rent"] = d["realised_rent"].fillna(d["rent_aed"])
    d["realised_yield"] = d["realised_rent"] / d["price_aed"] * 100
    d["total"] = d["realised_yield"] + d["change_pct"]
    return d


def excess(scored: pd.DataFrame, top: int = TOP) -> float | None:
    usable = scored.sort_values("yield_pct", ascending=False)
    picks, rest = usable.iloc[:top], usable.iloc[top:]
    if picks["total"].notna().sum() == 0 or rest["total"].notna().sum() == 0:
        return None
    return round(float(picks["total"].mean() - rest["total"].mean()), 2)


def permutation(rounds: list[pd.DataFrame], observed: float, draws: int = PERMUTATIONS, seed: int = 11) -> dict:
    """How often do random picks of the same size do at least as well across all rounds?"""
    rng = np.random.default_rng(seed)
    totals = np.zeros(draws)
    for frame in rounds:
        values = frame["total"].to_numpy()
        order = np.argsort(rng.random((draws, len(values))), axis=1)
        picks, rest = values[order[:, :TOP]], values[order[:, TOP:]]
        totals += np.nanmean(picks, axis=1) - np.nanmean(rest, axis=1)
    return {"observed_points": round(observed, 2), "random_95th_points": round(float(np.percentile(totals, 95)), 2),
            "share_of_random_at_least_as_good": round(float((totals >= observed).mean()), 3)}


def as_planned(table: pd.DataFrame, sales: pd.DataFrame, date: str, near: pd.DataFrame | None = None) -> float | None:
    """The plan's first method, kept for the record: estimated yield plus project and bedroom median change, against all options.

    The plan said "sales-weighted" without saying which sales. Pass near-line sales to weight by those instead of base-window sales.
    """
    d = sales[(sales["type"] == "Flat") & sales["project"].notna()]
    def medians(span):
        part = between(d, "date", span).assign(pps=lambda f: f["value"] / f["size"])
        g = part.groupby([*OPTION, "project"])["pps"].agg(["median", "size"])
        return g[g["size"] >= 3]
    both = medians(window(date, -6, 0)).add_suffix("_a").join(medians(window(date, 6, 12)).add_suffix("_b"), how="inner")
    both["log"] = np.log(both["median_b"] / both["median_a"]) * 100
    both["weight"] = both["size_a"]
    if near is not None:
        both["weight"] = near.groupby([*OPTION, "project"]).size().reindex(both.index).fillna(0)
        both = both[both["weight"] > 0]
    change = both.groupby(OPTION).apply(lambda g: np.average(g["log"], weights=g["weight"]), include_groups=False).rename("change")
    t = table.join(change, on=OPTION).sort_values("yield_pct", ascending=False)
    t["total"] = t["yield_pct"] + t["change"]
    return round(float(t.iloc[:TOP]["total"].mean() - t["total"].mean()), 2)


def wider_market(date: str, rents: pd.DataFrame, sales: pd.DataFrame, beta: float, change: pd.DataFrame) -> dict:
    """All ready flat sales at any price, scored the same way, so the price tier itself can be compared."""
    bought = between(sales, "date", (shift(date, -12, 1), date))
    bought = bought[bought["type"] == "Flat"]
    after = window(date, 0, 12)
    est = estimate_rents(bought, between(rents, "start", after), between(sales, "date", after), beta, tier_band=(0, 0))
    known = est[est["level"] != "none"]
    g = known.groupby(OPTION).agg(rent=("rent", "median"), price=("value", "median"), sales=("value", "size")).reset_index().merge(change, on=OPTION)
    weights = g["sales"]
    return {"yield_pct": round(float(np.average(g["rent"] / g["price"] * 100, weights=weights)), 2),
            "change_pct": round(float(np.average(g["change_pct"], weights=weights)), 2),
            "sales_covered_share": round(float(g["sales"].sum() / len(bought)), 2)}


def index_change(index: pd.DataFrame, base: tuple[str, str], end: tuple[str, str]) -> float | None:
    means = [index[index["month"].between(*span)]["flat"] for span in (base, end)]
    if end[1] > index["month"].max() or means[0].empty or means[1].empty:
        return None
    return round(float((means[1].mean() / means[0].mean() - 1) * 100), 1)


def hold_to_cut(scored: pd.DataFrame, near: pd.DataFrame, date: str, rents: pd.DataFrame, sales: pd.DataFrame, beta: float) -> dict:
    """Buy at the decision and hold to the data cut, with the transfer fee charged once. No selling costs or vacancy."""
    years = int(DATA_CUT[:4]) - int(date[:4])
    last = (shift(DATA_CUT, -6, 1), DATA_CUT)
    change = price_changes(sales, window(date, -6, 0), last)
    table = scored[["area_id", "rooms", "price_aed", "yield_pct", "size_sqm"]].merge(change, on=OPTION, how="left")
    table["income"] = 0.0
    for k in range(years):
        got = realised_rents(scored, near, window(date, 12 * k, 12 * (k + 1)), rents, sales, beta)
        table["income"] += table.join(got.rename("rent"), on=OPTION)["rent"] / table["price_aed"] * 100
    table["total"] = table["income"] + (np.exp(table["change_pct"] / 100) - 1) * 100 - FEE_PCT
    table["service"] = table["size_sqm"] * SERVICE_AED_PER_SQM / table["price_aed"] * 100 * years
    table = table.sort_values("yield_pct", ascending=False)
    picks, rest = table.iloc[:TOP], table.iloc[TOP:]
    return {"years": years, "picks_total_pct": round(float(picks["total"].mean()), 1), "others_total_pct": round(float(rest["total"].mean()), 1),
            "picks_extra_service_points_if_aed_200_per_sqm": round(float(picks["service"].mean() - rest["service"].mean()), 2)}


def run_round(date: str, rents: pd.DataFrame, sales: pd.DataFrame, index: pd.DataFrame) -> tuple[dict, dict[str, pd.DataFrame]]:
    table, near, beta = decide(date, rents, sales)
    ranked, _ = rank_ready(table, 0.0)
    after = window(date, 0, 12)
    realised = realised_rents(ranked, near, after, rents, sales, beta)
    scored, out = {}, {}
    for name, (base, end) in WINDOWS.items():
        change = price_changes(sales, window(date, *base), window(date, *end))
        scored[name] = score(ranked, realised, change)
        out[f"excess_{name}_points"] = excess(scored[name])
    plan = scored["plan"].sort_values("yield_pct", ascending=False)
    picks, rest = plan.iloc[:TOP], plan.iloc[TOP:]
    plan_change = price_changes(sales, window(date, -6, 0), window(date, 6, 12))
    wide = wider_market(date, rents, sales, beta, plan_change)
    plan_table = table[(table["stage"] == "ready") & (table["type"] == "Flat") & (table["project_share"] >= 0.5)]
    well_measured = scored["plan"].assign(total=lambda f: f["total"].where(f["matched"] >= MIN_MATCHED))
    official = index_change(index, window(date, -6, 0), window(date, 6, 12))
    out.update({
        "decision": date, "tested": date not in NO_TEST and len(rest) > 0, "options": len(plan),
        "picks": [f"{x.area}, {x.rooms}" for x in picks.itertuples()],
        "picks_estimated_yield_pct": round(float(picks["yield_pct"].mean()), 2),
        "picks_realised_yield_pct": round(float(picks["realised_yield"].mean()), 2), "others_realised_yield_pct": round(float(rest["realised_yield"].mean()), 2) if len(rest) else None,
        "picks_price_change_pct": round(float(picks["change_pct"].mean()), 2), "others_price_change_pct": round(float(rest["change_pct"].mean()), 2) if len(rest) else None,
        "excess_aed_per_10m": round(out["excess_plan_points"] / 100 * AMOUNT) if out["excess_plan_points"] is not None else None,
        "bottom_five_total_pct": round(float(plan.iloc[-TOP:]["total"].mean()), 2), "top_five_total_pct": round(float(picks["total"].mean()), 2),
        "as_planned_excess_points": as_planned(plan_table, sales, date),
        "as_planned_near_line_weights_excess_points": as_planned(plan_table, sales, date, near),
        "wider_market": wide, "picks_minus_wider_market_points": round(float(picks["total"].mean()) - wide["yield_pct"] - wide["change_pct"], 2),
        "official_flat_index_change_pct": official,
        "index_within_tolerance": None if official is None else bool(abs((np.exp(wide["change_pct"] / 100) - 1) * 100 - official) <= INDEX_TOLERANCE),
        "hold_to_data_cut": hold_to_cut(scored["plan"], near, date, rents, sales, beta) if len(rest) else None,
        "sensitivity": {
            "well_measured_options_only": excess(well_measured),
            "top_3": excess(scored["plan"], 3), "top_8": excess(scored["plan"], 8),
            "without_evidence_filter": excess(score((all_ready := table[(table["stage"] == "ready") & (table["type"] == "Flat")]), realised_rents(all_ready, near, after, rents, sales, beta), plan_change)),
            "near_line_sales_out_of_price_change": excess(score(ranked, realised, price_changes(sales, window(date, -6, 0), window(date, 6, 12), drop_near=True))),
            "picks_changed_by_30_day_embargo": _embargo_changes(date, rents, sales, picks),
        },
    })
    return out, scored


def _embargo_changes(date: str, rents: pd.DataFrame, sales: pd.DataFrame, picks: pd.DataFrame) -> int:
    table, _, _ = decide(date, rents, sales, embargo_days=30)
    ranked, _ = rank_ready(table, 0.0) if len(table) else (table, None)
    later = {tuple(x) for x in ranked.sort_values("yield_pct", ascending=False).iloc[:TOP][OPTION].to_numpy()} if len(ranked) else set()
    return TOP - len(later & {tuple(x) for x in picks[OPTION].to_numpy()})


def verdict(rounds: list[dict], tests: dict) -> dict:
    tested = [r for r in rounds if r["tested"]]
    both = sum((r["excess_plan_points"] or 0) > 0 and (r["excess_centred_points"] or 0) > 0 for r in tested)
    shown = all(t["observed_points"] > t["random_95th_points"] for t in tests.values())
    return {"shown": bool(shown), "label": "shown" if shown else "not shown", "tested_rounds": len(tested), "rounds_ahead_on_both_windows": int(both),
            "as_planned_rounds_ahead": sum((r["as_planned_excess_points"] or 0) > 0 for r in rounds),
            "as_planned_near_line_weights_rounds_ahead": sum((r["as_planned_near_line_weights_excess_points"] or 0) > 0 for r in rounds), "as_planned_rounds": len(rounds)}


def run(rents_raw: str, sales_raw: str, index_raw: str) -> dict:
    rents, funnel = clean(rents_raw, since="2020-11-01")
    sales = load_sales(sales_raw, since="2020-11-01")
    sales = sales[sales["stage"] == "ready"]
    index = duckdb.connect().execute(f"""SELECT left(first_date_of_month, 10) AS month, try_cast(flat_monthly_index AS DOUBLE) AS flat
        FROM read_csv('{index_raw}', header=true, all_varchar=true) WHERE flat_monthly_index IS NOT NULL ORDER BY 1""").df()
    results, scored = zip(*(run_round(d, rents, sales, index) for d in ROUNDS))
    tested = [(r, s) for r, s in zip(results, scored) if r["tested"]]
    tests = {name: permutation([s[name] for _, s in tested], sum(r[f"excess_{name}_points"] for r, _ in tested)) for name in WINDOWS}
    rent_gap = sum(r["picks_realised_yield_pct"] - r["others_realised_yield_pct"] for r, _ in tested)
    rent_only = permutation([s["plan"].assign(total=lambda f: f["realised_yield"]) for _, s in tested], rent_gap)
    return {"funnel": funnel, "verdict": verdict(list(results), tests), "permutation": tests,
            "rent_only_permutation_added_after_seeing_results": rent_only, "rounds": list(results)}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rents", default="data/raw/rents/*.csv.gz")
    p.add_argument("--sales", default="data/raw/transactions/*.csv.gz")
    p.add_argument("--index", default="data/raw/price_index/*.csv")
    p.add_argument("--out", default="validation/backtest.json", type=Path)
    a = p.parse_args()
    a.out.write_text(json.dumps(run(a.rents, a.sales, a.index), indent=1, default=float) + "\n")
    print(f"wrote {a.out}")
