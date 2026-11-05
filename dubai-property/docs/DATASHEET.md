# Datasheet: Dubai real estate transactions

## Source

- **Publisher:** Dubai Land Department, through [Data.Dubai](https://data.dubai/en/l/470061).
- **Downloaded:** 5 November 2026, from the release dated 4 November 2026.
- **Licence:** [Data.Dubai's FAQ](https://data.dubai/en/faqs) places open data under Dubai's Open Data License, which allows commercial and non-commercial use subject to its terms. The full licence text has not been reviewed yet.

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

## Known traps

- **Not every row is a sale.** Mortgages and gifts share the file, so price work must filter to sales.
- **Sales are not all alike.** The 2026 export shows pre-registration, delayed, development and lease-to-own procedures. Which count as market prices is still to be decided.
- **Repeated values.** In the 2026 export, bulk mortgage deals show the full deal value on each unit's row.
- **Mislabelled property.** In the 2026 export, offices and shops appear under Residential usage.
- **Odd dates.** Some early dates are not Gregorian, such as `1416-07-02`.
- **Commas in names.** Project names can contain commas, so these files need a strict CSV reader.
- **Not checked yet:** duplicates beyond the transaction ID, outliers, area name changes and how far each field is filled in across years.

## Limits

- Values are registered amounts and may differ from market prices.
- There are no buyer or seller names, and no visa status, so any Golden Visa effect can only be inferred.
- Rents and the price index are separate datasets, not downloaded yet.
