# Model card: day-ahead demand forecast

## What it does

Predicts electricity demand for each half-hour of the next day, in each of 5 market regions, with a likely range. It issues at midnight market time before the target day. Code: `pipeline/forecast.py`.

**Intended use:** showing how far a demand forecast can be trusted in analysis. **Not for** market operation, trading or grid decisions.

## How it works

- **Model:** scikit-learn `HistGradientBoostingRegressor`, one set per region, retrained for each test year.
- **Settings:** fixed in advance, not tuned, so test years cannot influence them: 300 iterations, learning rate 0.06, 48 leaf nodes, at least 40 samples per leaf, L2 of 1.0, seed 42.
- **Features:** demand 2, 4, 7 and 14 days earlier; the mean of the prior 7 days; calendar and holidays; local hour. The weather version adds temperature, heating and cooling degrees and radiation.
- **Likely range:** 10th and 90th percentile models on the no-weather features, widened by a margin from errors on the final training year.

## How it was tested

Expanding window: train on all earlier years, then predict FY2024, FY2025 and FY2026 in turn. The baseline assumes demand matches the same time last week.

**FY2026 typical error (WAPE), by region:**

| Region | Baseline | No weather | With observed weather |
|---|---|---|---|
| New South Wales | 10.1% | 6.0% | 4.1% |
| Queensland | 7.3% | 4.5% | 3.3% |
| South Australia | 18.6% | 12.3% | 7.8% |
| Tasmania | 7.5% | 5.9% | 5.3% |
| Victoria | 11.9% | 8.0% | 5.9% |

Every region and year is in `validation/forecast_metrics.json`, including peak-hour accuracy and bias.

**Likely range:** targets 80% coverage. Actual coverage is 73% to 83% across regions and years, so it can run a little short.

## Limits

- **Observed weather flatters the weather version,** because nobody knows tomorrow's weather exactly. A real forecast would sit between the no-weather and with-weather figures.
- **The range belongs to the no-weather model.** The with-weather line falls outside it 6.2% of the time, against 0.8% for the no-weather line, so charts pair it with the no-weather line.
- **South Australia is hardest to predict,** with the largest errors.
- **Not compared with AEMO's own forecast,** so this shows improvement over a simple baseline, not over the industry's forecast.
