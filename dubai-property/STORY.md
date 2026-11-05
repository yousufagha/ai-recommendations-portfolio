# Dubai Golden Visa in everyday language

Work in progress. The first finding is below, and the rankings and paper test are still to come.

## First finding

**Demand gathers at the Golden Visa line, and no clear extra cost is proven.** From Q2 2022, residential sales just above AED 2 million outnumber those just below it by 1.56 to 1, up from 1.10 to 1 in 2015 to 2021. Nearby prices such as AED 1.9M, 2.1M and 2.2M sit between 0.98 and 1.11.

When similar-sized homes in the same building and year are compared, a first reading of about AED 39,000 (+1.9%, range AED 14,000 to 63,000) appears at the line. Prices with no visa line show swings of a similar size, from -2.2% to +1.7%, so this is not claimed as a real cost.

**What it means for a buyer with about AED 2 million:** reaching the line does not appear to carry a clear premium, so choose the home on value and returns. As a precaution, compare price per square metre with similar homes in the same building.

The records do not show who received a visa, so the link to the visa is inferred. Floor and view are not in the data. Figures come from [the results file](validation/value_at_line.json), and `make dubai` rebuilds them.

## Second finding

**At the same AED 2 million, ready homes differ by up to AED 30,000 a year in estimated rent.** Among 13 ready flat options that could be ranked, gross yield runs from 5.2% to 6.4%, or AED 105,000 to AED 135,000 a year. Four share the top tier, because the gaps between them are smaller than the estimate's typical error of 0.67 points: Business Bay 2-bed (6.4%), Hadaeq Sheikh Mohammed Bin Rashid 2-bed (6.1%), Business Bay 1-bed (6.0%) and Hadaeq Sheikh Mohammed Bin Rashid 1-bed (6.0%).

**What it means for a buyer with about AED 2 million who wants income:** start with these four and compare actual buildings, because the same price can buy noticeably more rent. Off-plan was 76% of sales in this price band, but earns no rent until handover, so we show it separately as indicative.

These are gross figures for homes priced at the threshold, before service charges, vacancy and fees, none of which are in the data. Rents come from new contracts in the year to 3 November 2026, because renewals lag the market. Estimates held up in three checks: applied to projects whose real rent was known, they showed no overall lean, with a typical miss of 0.67 points; last year's rents gave a similar order (rank correlation 0.90); and the Business Bay reading sits close to a [published 6.6%](https://joinoliva.com/en/learn/blog/dubai-rental-yields-by-area-2026-ejari-data) from a commercial source. Whether these homes would have beaten the market is not yet tested. Figures come from [the results file](validation/rent_yields.json).

## Third finding: the test on past years

**The ranking found homes that went on to earn more rent. Better total return is not shown.** Each November from 2022 to 2025 we picked five AED 2M homes using only what was known that day, then compared them with the other ranked options over the next year.

- **Rent:** the picks earned 0.5 to 0.7 points more in new rents agreed afterwards, in all four rounds. On a paper AED 10 million, that is AED 50,000 to AED 73,000 a year before costs. Across the rounds, the gap of 2.41 points beat all 5,000 random picks.
- **Total return, rent plus price change:** not shown. The picks were ahead in three of four rounds on both ways of measuring price, by 1.08 to 3.02 points. The summed gap beat 95% of random picks on one measure (16.94 points) but not the other (3.78 points). Limited to options with at least 100 matched sales, the gaps were +2.25, -0.35, -0.51 and +0.44 points.
- **Against the wider market:** AED 2M picks trailed all ready flats in three of four rounds. Homes across all prices often earn a higher rental yield, so the visa is part of what a threshold buyer gets for their money.

**What it means for a buyer with about AED 2 million:** use the ranking to choose for rental income. Do not rely on it to predict which homes will rise most in price.

Limits: four rounds in one market cycle cannot prove much. Even a real edge of 1 to 2 points a year would usually read as "not shown". Figures are before service charges, vacancy and selling costs. Results use rents and sales as published now, because the records do not show when each was registered. The official flat index ends in May 2024, so it can check only two rounds: it matched in 2022 (14.7% against 14.6%) and differed in 2021 (27.0% against 8.4%), which is why 2021 is shown with no dirham figures. This was not a blind test: a reviewer ran the original plan before the final method was set, and [the decisions log](DECISIONS.md) records what changed. Figures come from [the results file](validation/backtest.json).

## In 30 seconds (to finalise)

"In Dubai, buying AED 2 million of property can come with long-term residency. I took the official sales records and used AI to answer two questions: do buyers pay extra to reach that line, and which ways of spending that money would have earned the most? Then I tested the advice on years it had never seen, against simply buying the whole market. [Result, from the data.]"

## In 2 minutes (to complete)

- **Why it matters:** a home is a very large decision, and here it can also decide where a family can live. Clear numbers help people choose well, and the official records show what sold, where and for how much.
- **The scale:** 1,386,564 sales in the official records, mostly from 2008 to 3 November 2026.
- **How it works:**
  1. **Collect:** gather the official records, keep real sales, and set aside mortgages and gifts, so a mortgage is not mistaken for a sale price.
  2. **Look for a pattern:** see if sales crowd just above AED 2 million, then check whether the same happens at other round numbers, because people like round numbers anyway.
  3. **Predict:** a model learns what similar homes sell for and how each area tends to move over the next year.
  4. **Advise:** rank the options in dirhams, after costs and risk. AI writes the advice in plain English, and an automatic check rejects it if any number is wrong.
  5. **Show:** a public report anyone can open, starting with what to do.
- **How we know it's right:** the advice was tested as if investing a paper AED 10 million in past years, using only what was known at the time. It had to beat buying the whole market. Rent: yes, in all four rounds. Total return: not shown.
- **What it means:** [buyers: best way to qualify. Developers: whether to price at the line. Advisers: where the market is. Government: what happens if the line moves.]

## If someone asks

- **Is this advice?** No. It is analysis of public records, not immigration or investment advice.
- **Do you know who got a visa?** No. The records do not appear to show that, so any visa effect is inferred from price patterns.
- **Could you really have made that money?** Not exactly. It is a simulation by area, and nobody can buy at an area's typical price.
- **What are the visa rules?** Details are updated over time, so check the current terms with the authorities.
