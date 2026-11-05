# Grid Pulse in everyday language

Figures from the build on 5 November 2026. All dollar figures are Australian dollars at wholesale market prices.

## In 30 seconds

"Electricity in Australia is traded every five minutes, and the price can swing from below zero to thousands of dollars. I took nearly eight years of official records, about 2.9 million of them, and built a system that shows when power is cheap or expensive and predicts tomorrow's demand. Then I turned it into advice. For example, a business that can run equipment a few hours earlier in South Australia could avoid about $150,000 a year per megawatt at market prices."

## In 2 minutes

**Why it matters.** Everyone pays for electricity, but few people see how the price is set. Behind every power bill is a live market covering New South Wales, Queensland, South Australia, Tasmania and Victoria. Prices change constantly, and a handful of extreme moments can drive a large share of the cost.

**The scale.** The project covers January 2019 to October 2026: about 2.9 million records and roughly 1,440 terawatt-hours of electricity demand, worth about $150 billion at market prices. Prices ranged from minus $1,000 to $23,200 per megawatt-hour. In household terms, that is from minus $1 to $23.20 per kilowatt-hour on the wholesale market alone.

**How it works.**
1. **Collect:** it downloads the market operator's 470 monthly files, plus weather records for 11 cities.
2. **Clean up:** in October 2021 the market went from a record every 30 minutes to one every 5 minutes. A simple average would give the wrong answer, in the way that averaging prices at a shop without counting how much was bought would. So every sum weighs prices by the amount of electricity involved.
3. **Predict:** a machine learning model acts like a weather forecast for electricity demand, predicting each half-hour of the next day.
4. **Show:** a public Looker Studio report will put all this in front of decision-makers, starting with what to do. This part is still to be built.

**How we know it's right.** Automated tests check the calculations, and the records have no duplicates or gaps. The forecast was tested fairly: it only learned from earlier years, then predicted three full years it had never seen. In the latest of those years, its typical error was 4.5% to 12.3%, depending on the region, against 7.3% to 18.6% for the simple method of assuming demand matches the same time last week. With actual weather it does better, at 3.3% to 7.8%, but that flatters it, because nobody knows tomorrow's weather exactly. The real figure would sit between those two ranges.

**What it means.**
- **Retailers:** in South Australia, the dearest 1% of moments made up 35% of wholesale cost, so insurance against them is worth keeping even after a quiet year.
- **Businesses:** midday power is far cheaper than early-evening power, so shifting flexible work earlier can save real money.
- **Battery investors:** the headline earnings are best-case figures, so plans should be tested against much lower ones.
- **Policy makers:** Victoria's wholesale price was below zero 26% of the time in the latest financial year, up from 19% three years earlier, though the latest few months were lower than the same months a year before. Pricing could encourage people to use power at those times.

## If someone asks

- **Is this advice?** No. It is analysis of public data, and each recommendation states its limits.
- **Will these savings definitely happen?** No. They are at market prices, before network charges and contract terms.
- **What is still weak?** The forecast's "likely range" should catch actual demand about 80% of the time. It first caught only 60% to 72%, so I corrected it using a year of past errors, and it now catches 73% to 83%, depending on the region and year. South Australia remains the hardest region to predict.

Data: AEMO, used with attribution. Weather data by [Open-Meteo.com](https://open-meteo.com/), CC BY 4.0.
