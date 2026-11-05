# Decisions

- 2026-11-05: This project comes first, because the UAE is needed sooner.
- 2026-11-05: The headline is the AED 2 million Golden Visa question; the fair-price model is a measuring tool, not the deliverable.
- 2026-11-05: Objective: AI recommendations that show in dirhams who profits and by how much, then test whether they would have worked.
- 2026-11-05: "Us" is an advisory firm selling this analysis to investors and developers.
- 2026-11-05: Report in Tableau Public; only area-level summaries are uploaded, because viewers can download published data.
- 2026-11-05: Row-level access is dropped, because a public report cannot show it; Superset stays a possible add-on.
- 2026-11-05: Publish the paper-investment result even if the engine loses to the market or the simple rule.
- 2026-11-05: Official sources conflict on visa length and mortgages; the report shows the conflict rather than choosing.
- 2026-11-05: Claude memo text is generated once and stored, and fails if any number differs from the results file.
- 2026-11-05: Scope is the property decision only, with separate rankings for living in the home and renting it out.
- 2026-11-05: AI results are computed in advance, because Tableau Public cannot call AI live; viewers explore them with filters.
- 2026-11-05: Raw transactions are public in the repo, split by year and gzipped, because GitHub refuses files over 100 MB.
- 2026-11-05: data.dubai is the source for history, because the Land Department page only reaches back to January 2026.
- 2026-11-05: Test value at AED 2M against other round prices, nearby prices and earlier years, because prices cluster at round numbers anyway.
- 2026-11-05: Treat the value step at AED 2M as unproven, because prices with no visa line show steps of similar size. No saving is claimed from it.
- 2026-11-05: The landing page is built from a template and the results files by `pipeline/build_site.py`, and tests fail if a written claim stops holding, so charts cannot drift from the analysis.
- 2026-11-05: Dashboards are Tableau Public for Dubai and Looker Studio for Grid Pulse. Superset is dropped because a public link would need a paid server.
