# AI recommendations portfolio

[![Tests](https://github.com/yousufagha/ai-recommendations-portfolio/actions/workflows/tests.yml/badge.svg)](https://github.com/yousufagha/ai-recommendations-portfolio/actions/workflows/tests.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Code licence: MIT](https://img.shields.io/badge/code%20licence-MIT-green.svg)](LICENSE)

Recommendations that show, in money, who profits and by how much, then test whether they would have worked.

| Project | Question | Status |
|---|---|---|
| [Dubai Golden Visa](dubai-property/) | Does AED 2 million buy more than a property, who profits from that, and what is the best way to use it? | Data collected, analysis not started |
| [Grid Pulse](grid-pulse/) | When is Australian electricity cheap or expensive, and who could save money by acting on it? | Pipeline, forecast and recommendations built; dashboard not started |

## Grid Pulse so far

- 2.9 million market records from January 2019 to October 2026, about $150 billion at market prices.
- In FY2026, the dearest 1% of intervals carried 35% of South Australia's wholesale cost.
- The day-ahead demand forecast beat a same-time-last-week baseline in every region on years it never saw. In FY2026, its typical error was 4.5% to 12.3%, against 7.3% to 18.6%.

Read [the story in everyday language](grid-pulse/STORY.md) or [the recommendations](grid-pulse/RECOMMENDATIONS.md).

## Free data

**[Download the raw data](DATA.md):** 1.8 million Dubai real estate transactions, plus Australian electricity prices, demand and weather. No login needed.

## Dubai Golden Visa so far

- 1,813,436 official transaction records, of which 1,386,564 are sales, in yearly files under [`dubai-property/data/raw/transactions/`](dubai-property/data/raw/transactions/). Most records fall from 2008 onwards.
- No findings are claimed yet. Read [the planned story](dubai-property/STORY.md).

## Run it

Install the locked versions, then run the tests:

```bash
make setup
```

```bash
make test
```

Rebuild every Grid Pulse result from the committed raw data:

```bash
make grid-pulse
```

## How this repo is maintained

See [the repository practices](docs/REPO_PRACTICES.md), including what is still to do.

## Data and credits

The MIT licence covers the code only. Data stays under its publishers' terms.

- **Dubai Land Department:** via [Data.Dubai](https://data.dubai/en/l/470061), under the [Open Data Licence](dubai-property/data/raw/README.md). This repo is independent and not endorsed by any government entity. Files are split by year and compressed, and [the manifest](dubai-property/data/raw/transactions/manifest.json) records the row counts and source checksums.
- **Australian Energy Market Operator (AEMO):** market data used with attribution under [AEMO's copyright permissions](https://www.aemo.com.au/privacy-and-legal-notices/copyright-permissions).
- **Weather:** data by [Open-Meteo.com](https://open-meteo.com/), [CC BY 4.0](https://open-meteo.com/en/licence).

This is analysis of public data. It is not financial, investment or immigration advice.
