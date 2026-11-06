# Tableau Public dashboard: AED 2M homes

Start here. These files hold tested results as flat tables. `make dubai` rebuilds them with `pipeline/build_tableau.py`, and a test fails if they drift from `validation/`.

**Cost:** [Tableau Public web authoring is free](https://help.tableau.com/current/pro/desktop/en-us/public_faq.htm). Everything published is public, which suits this open data. Build on a computer, not a phone.

**Status, 6 November 2026:** sheets 1 to 3 are built in Tableau Public and checked against the tested figures. The rest are still to build.

## Files

| File | One row is | Use |
|---|---|---|
| `options.csv` | A home option: area, bedrooms, type, stage group | Rankings. Filter `group` to `Ready, ranked` for the main chart. |
| `backtest_rounds.csv` | A yearly decision | Rent and total-return test |
| `backtest_picks.csv` | A home picked in a round | What the method chose |
| `price_steps.csv` | A price point | Whether AED 2M carries extra cost |
| `crowding_by_quarter.csv` | A quarter and series | Demand at the line |
| `sales_bands_2025.csv` | An AED 25,000 price band | Sales around AED 2M |
| `sales_by_year.csv` | A year | Market growth. 2026 runs to 3 November. |
| `rents_by_year.csv` | A year and type | Median rent, all new and renewed single-home contracts |

## Build

1. On [Tableau Public](https://public.tableau.com/), choose **Create**, then **Web Authoring**, and upload `options.csv`. GitHub shows CSVs as text, so use Save As or download from the repository.
2. Add the other CSVs with **Data**, then **New Data Source**. Do not join them: they share no row-level key.
3. Saving means publishing, and everything published is public. Keep the tab open while building, and add the disclaimers before the first publish.
4. Build these sheets, then arrange them on one dashboard in this order:

| Sheet | Form | Fields | Note on it |
|---|---|---|---|
| **Top homes for rent** | Horizontal bars | `home` by `gross_yield_pct`, sorted. Colour by `top_tier`. Tooltip: `rent_aed`, `sales`, `project_evidence_share`. | Highlighted homes are too close to separate. Estimates typically miss by 0.67 points. |
| **Did it work?** | Two lines | `decision` on Columns, **Measure Values** on Rows keeping only `picks_rent_pct` and `others_rent_pct`, **Measure Names** on Color. Aliases: Picked homes, Other ranked homes. Axis: Yearly rent, % of price, from 0. | Filter `tested` to True. |
| **Total return: the ranking is for rent, not price** | Table | `decision` on Rows, Measure Names on Columns, Measure Values on Text, keeping `total_gap_first_price_measure`, `total_gap_second_price_measure`, `total_gap_well_measured_only`. Aliases: Price measure A, Price measure B, Well-measured homes only. | Show the verdict line below. |
| **Demand at the line** | Two lines | `quarter` by `sales_above_per_sale_below`, colour by `series` | 1 means even. |
| **No clear extra cost** | Dots with ranges | `price_aed` by `step_pct`, from `low_pct` to `high_pct`, highlight `visa_line` | Prices with no visa line swing by similar amounts. |
| **Off-plan, indicative** | Table | `options.csv` filtered to `Off-plan, indicative` | Today's rents. No income until handover. Never merge with the ranked table. |

Colours: blue `#2a78d6`, orange `#eb6834`, grey `#c4c2ba`. Keep text in black or grey. One axis per chart.

## Words to use

**Title:** At AED 2 million, which Dubai homes earn the most rent?

**Headline:** The AI ranking picked homes that earned more rent than the other ranked options in every test round, worth AED 50,000 to 73,000 a year on AED 10 million, before costs.

**Verdict line:** Rent edge: delivered in 4 of 4 rounds. Total-return edge: not shown, so we don't claim one. Choose these homes for income.

**Also show:** Across all prices, ready flats often earn a higher yield, and the picks trailed them on total return in 3 of 4 rounds, so the visa is part of what a threshold buyer gets for their money.

**Recommendation:** Use the ranking to choose for rental income, not to predict price rises.

**Always show on the dashboard:**

> Gross yields, before service charges, vacancy and fees. Homes priced at the threshold, not confirmed visa cases. Four test rounds in one market cycle cannot prove much, and the test was not blind. Dubai data: Dubai Land Department, via Data.Dubai, under the Open Data Licence. An independent project, not endorsed by or affiliated with any government entity. Analysis of public data, not financial, investment or immigration advice.

Link back to `https://yousufagha.github.io/ai-recommendations-portfolio/`.

## Keep out

Do not say "qualifying homes", and do not state off-plan, mortgage or joint-ownership visa rules as fact until the Dubai Land Department confirms them. Do not show dirham levels for 2021, because that round's price measure differs from the official index.
