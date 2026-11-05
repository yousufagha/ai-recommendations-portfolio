# Datasheet: Dubai real estate data

## Source

- **Publisher:** Dubai Land Department, through [Data.Dubai](https://data.dubai/en/l/470061).
- **Downloaded:** 5 November 2026, from the release dated 4 November 2026.
- **Licence:** the [Open Data Licence](https://data.dubai/documents/d/guest/open-data-license-english-5-pdf), which allows public sharing and commercial use subject to its terms. See [the data notice](../data/raw/README.md).

## What is here

| File | Contents |
|---|---|
| `data/raw/transactions/transactions_*.csv.gz` | All 1,813,436 published rows, split by year, as text |
| `data/raw/transactions/manifest.json` | Row counts per file and checksums of the two source files |
| `data/raw/transactions-2026-11-05.csv` | A separate 2026 export from the [Land Department page](https://dubailand.gov.ae/en/open-data/real-estate-data/), 185,212 rows, with different column names |

The two source files were split by `pipeline/split_raw.py`. Rows, unique transaction IDs, sales counts and total value all match the originals.

## Coverage

- **By type:** 1,386,564 of the 1,813,436 rows are sales.
- **By time:** thin before 2008, when 47,243 rows are spread over decades, then every year to 3 November 2026. Sales range from 23,633 in 2008 to 214,568 in 2025, so recent years dominate.
- **Fields:** date, group and procedure, value, area, usage, property type, rooms, size, price per square metre, project, nearest landmarks and party counts, mostly in Arabic and English.

## Reading the data well

- **Not every row is a sale.** Mortgages and gifts share the file, so price work must filter to sales.
- **Sales are not all alike.** The 2026 export shows pre-registration, delayed, development and lease-to-own procedures. Which count as market prices is still to be decided.
- **Bulk deals.** In the 2026 export, bulk mortgage deals show the full deal value on each unit's row.
- **Broad usage labels.** In the 2026 export, offices and shops can sit under Residential usage, so filter by sub-type too.
- **Older calendar dates.** Some early dates do not appear to use the Gregorian calendar, such as `1416-07-02`.
- **Commas in names.** Project names can contain commas, so these files need a strict CSV reader.
- **Similar rows.** From 2019, 33,695 sales rows (3.8%) share a date, place, value and size with another row. These may be separate identical units, so treat them with care.
- **Fill rates from 2019.** Value, size and area are complete. Project is 89% filled, rooms 86% and building 79%.
- **Not checked yet:** outliers and area name changes.

## Rent contracts

- **Source:** [Rent Contracts on Data.Dubai](https://data.dubai/en/l/468586), tagged Open, released 4 November 2026, downloaded 5 November 2026.
- **Files:** `data/raw/rents/`, all 10,683,846 published lines, in 22 files by contract start year. A full-value checksum matched the 11 source files.
- **Coverage:** 7,555,484 residential lines. Residential lines rise from 307,687 starting in 2014 to 826,260 in 2025.
- **One contract can have several lines.** There are 8,915,150 contract IDs, and `contract_id` with `line_number` is unique.
- **Annual and contract amounts differ on 806,260 residential lines,** so use `annual_amount` for yearly rent.
- **Whole-building and bulk contracts.** 1,511,943 residential lines cover more than one property, and 140,169 exceed AED 5 million a year, so filter on `no_of_prop` before estimating a home's rent.
- **Labour accommodation and virtual units** can appear under Residential usage, so filter by property type too.
- **Project is 25% filled for 2026,** so area is the reliable place field. 177 of the 215 rent area names also appear in the 2025 sales file, so the rest need matching.
- **Dates:** a few starts run far ahead, such as `2205-07-16`. They sit in `rents_after-2027.csv.gz`.
- **Renewals lag new contracts.** Flats starting in 2025 had a median of AED 971 per sqm new and AED 693 renewed, so use new contracts for market rent.
- **`actual_area` needs bounds.** It runs from 1 sqm to 378,236 sqm on single-property lines. `pipeline/clean_rents.py` keeps 15 to 2,000 sqm and records every step's count in `validation/rent_yields.json`.
- **Project is on under half of new contracts,** and not at random: rents with a project run higher. Do not mix project and area figures without saying so.
- **Not in the data:** furnished status, holiday lets and handover dates.
- **Fields on people:** the files have no names, phone numbers or unit numbers. They do hold contract IDs and tenant type, and the portal has listed `Personal Information (DNRD)` under Rights for this dataset. Aggregate before publishing analysis.

## Residential sale index

`data/raw/price_index/` holds the [Residential Properties Sale Index](https://data.dubai/en/l/468732) unchanged. It has 159 monthly rows from March 2011 to May 2024, so its latest value is May 2024 despite the November 2026 file date. Use the sales records for newer price moves. Quarterly and yearly columns are often blank.

## Limits

- Values are registered amounts and may differ from market prices.
- There are no buyer or seller names, and no visa status, so any Golden Visa effect can only be inferred.
