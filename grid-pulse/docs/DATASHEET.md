# Datasheet: Australian electricity market and weather

## Source

- **Market data:** Australian Energy Market Operator (AEMO) monthly price and demand files, downloaded on 5 November 2026 by `pipeline/fetch_aemo.py`. [AEMO's terms](https://www.aemo.com.au/privacy-and-legal-notices/copyright-permissions) allow any purpose with accurate attribution.
- **Weather:** hourly records for 11 cities from [Open-Meteo.com](https://open-meteo.com/), [CC BY 4.0](https://open-meteo.com/en/licence), downloaded by `pipeline/fetch_weather.py`.

## What is here

| Path | Contents |
|---|---|
| `data/raw/aemo/` | 470 monthly CSVs: 94 months for each of 5 regions, January 2019 to October 2026 |
| `data/raw/weather/` | One JSON file per city |
| `data/star/` | Not committed; rebuilt by the pipeline |

The built fact table has 2,915,040 rows, with no duplicates or gaps at the declared interval length.

## Known traps

- **Interval length changes.** Rows are 30-minute up to the one ending 1 October 2021 at 00:00, then 5-minute, so plain averages across the change are wrong. Totals use energy, which is demand x interval hours.
- **Timestamps mark the end of the interval.** Market time is fixed at UTC+10, so a 00:00 row belongs to the previous day, and clock times differ from local time during daylight saving.
- **Two prices.** Energy-weighted price is what the market's load paid. Time-weighted price values a flat 1 MW. South Australia's FY2026 weekday evening-to-solar gap is $174/MWh on the first and $145/MWh on the second.
- **Partial years.** FY2019 and FY2027 are partial, and FY2022 spans the interval change.
- **June 2022.** Administered pricing rows are kept but not yet flagged in the data.
- **Negative demand.** South Australia has 1,423 intervals of negative demand, kept as published.

## Limits

- `TOTALDEMAND` is AEMO's regional measure, not total consumption, and excludes rooftop solar.
- Prices are wholesale, before network charges and contract terms.
- City weights are rounded approximations of population share.
