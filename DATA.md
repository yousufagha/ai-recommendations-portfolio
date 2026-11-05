# Download the data

Free raw data, ready to use, with no login. Clone the repo or use the direct links below.

## Dubai real estate transactions

1,813,436 transaction records, including 1,386,564 sales, mostly from 2008 to 3 November 2026. Each record has value, area, project, property type, rooms, size, price per square metre and nearest landmarks.

| File | Format | Link |
|---|---|---|
| Yearly transaction files | Compressed CSV, up to 95 MB each | [Browse the folder](dubai-property/data/raw/transactions/) |
| 2025 transactions | Compressed CSV | [Download](https://raw.githubusercontent.com/yousufagha/ai-recommendations-portfolio/main/dubai-property/data/raw/transactions/transactions_2025.csv.gz) |
| 2026 export, with different column names | CSV | [Download](https://raw.githubusercontent.com/yousufagha/ai-recommendations-portfolio/main/dubai-property/data/raw/transactions-2026-11-05.csv) |
| Row counts and checksums | JSON | [Manifest](dubai-property/data/raw/transactions/manifest.json) |

Fields and tips for reading the data are in [the datasheet](dubai-property/docs/DATASHEET.md). Terms are in [the data notice](dubai-property/data/raw/README.md).

### Try it in Python

```python
import duckdb

url = "https://raw.githubusercontent.com/yousufagha/ai-recommendations-portfolio/main/dubai-property/data/raw/transactions/transactions_2025.csv.gz"
print(duckdb.sql(f"""
    SELECT area_name_en, count(*) AS sales, median(actual_worth::DOUBLE) AS median_aed
    FROM read_csv('{url}', header=true, all_varchar=true, delim=',', quote='"', escape='"')
    WHERE trans_group_en = 'Sales'
    GROUP BY 1 ORDER BY sales DESC LIMIT 10
"""))
```

## Australian electricity and weather

Half-hourly and 5-minute prices and demand for 5 market regions from January 2019 to October 2026, and hourly weather for 11 cities.

| Files | Format | Link |
|---|---|---|
| 470 monthly market files | CSV | [Browse the folder](grid-pulse/data/raw/aemo/) |
| Weather for 11 cities | JSON | [Browse the folder](grid-pulse/data/raw/weather/) |

Details are in [the datasheet](grid-pulse/docs/DATASHEET.md).

## Insights built on this data

- [Grid Pulse recommendations](grid-pulse/RECOMMENDATIONS.md), with [the story in everyday language](grid-pulse/STORY.md)
- [Dubai Golden Visa analysis](dubai-property/STORY.md), in progress

## Terms and credit

The MIT licence covers the code only. Each dataset stays under its publisher's terms:

- **Dubai transactions:** from the Dubai Land Department via [Data.Dubai](https://data.dubai/en/l/470061), under the [Open Data Licence](https://data.dubai/documents/d/guest/open-data-license-english-5-pdf). This repo is independent and is not endorsed by or affiliated with any government entity.
- **Electricity:** Australian Energy Market Operator, under [its copyright permissions](https://www.aemo.com.au/privacy-and-legal-notices/copyright-permissions).
- **Weather:** [Open-Meteo.com](https://open-meteo.com/), [CC BY 4.0](https://open-meteo.com/en/licence).

To cite this repo, use [`CITATION.cff`](CITATION.cff).
