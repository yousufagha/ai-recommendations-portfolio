# Contributing

This is a personal portfolio, but corrections are welcome, especially a wrong figure or a misread source.

1. Open an issue first, using a template, so we can agree the change.
2. Install and test with `make setup` and `make test`.
3. Keep each commit to one change. Run `make lint` before opening a pull request.
4. A pull request merges only after its tests pass.

**Data:** never edit raw files. Fix the pipeline instead, and record any data decision in that project's `DECISIONS.md`.

**Figures:** every published figure must trace to a tested script or a results file. Findings that weaken a recommendation stay in.

Fuller rules are in [the repository practices](docs/REPO_PRACTICES.md).
