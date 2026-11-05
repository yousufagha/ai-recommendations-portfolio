# Dubai Golden Visa in everyday language

Work in progress. The first finding is below, and the rankings and paper test are still to come.

## First finding

**Demand gathers at the Golden Visa line, and no clear extra cost is proven.** From Q2 2022, residential sales just above AED 2 million outnumber those just below it by 1.56 to 1, up from 1.10 to 1 in 2015 to 2021. Nearby prices such as AED 1.9M, 2.1M and 2.2M sit between 0.98 and 1.11.

When similar-sized homes in the same building and year are compared, a first reading of about AED 39,000 (+1.9%, range AED 14,000 to 63,000) appears at the line. Prices with no visa line show swings of a similar size, from -2.2% to +1.7%, so this is not claimed as a real cost.

**What it means for a buyer with about AED 2 million:** reaching the line does not appear to carry a clear premium, so choose the home on value and returns. As a precaution, compare price per square metre with similar homes in the same building.

The records do not show who received a visa, so the link to the visa is inferred. Floor and view are not in the data. Figures come from [the results file](validation/value_at_line.json), and `make dubai` rebuilds them.

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
- **How we know it's right:** the advice was tested as if investing a paper AED 10 million in past years, using only what was known at the time. It had to beat buying the whole market. [Result, whichever way it went.]
- **What it means:** [buyers: best way to qualify. Developers: whether to price at the line. Advisers: where the market is. Government: what happens if the line moves.]

## If someone asks

- **Is this advice?** No. It is analysis of public records, not immigration or investment advice.
- **Do you know who got a visa?** No. The records do not appear to show that, so any visa effect is inferred from price patterns.
- **Could you really have made that money?** Not exactly. It is a simulation by area, and nobody can buy at an area's typical price.
- **What are the visa rules?** Details are updated over time, so check the current terms with the authorities.
