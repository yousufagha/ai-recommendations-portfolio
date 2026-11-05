# Datasheet: Dubai real estate transactions

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

## Limits

- Values are registered amounts and may differ from market prices.
- There are no buyer or seller names, and no visa status, so any Golden Visa effect can only be inferred.
- Rents and the price index are separate datasets, not downloaded yet.
