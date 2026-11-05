# How this repo is maintained

Sources checked on 5 November 2026. Status: **In place** is true of the repo today, and **To do** is not yet.

## Data

| Rule | Why | Status |
|---|---|---|
| Raw data is never edited, and derived data is rebuilt from it | [Cookiecutter Data Science](https://cookiecutter-data-science.drivendata.org/opinions/): raw data "must be treated as immutable" | In place |
| Any reshaping of raw files keeps a manifest of row counts and source checksums, and a test checks it | Proves nothing was lost | In place for Dubai transactions and rents |
| Each file stays under 95 MB | [GitHub enforces 100 MB per file and recommends 1 MB](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits) | In place |
| Each dataset has a datasheet: source, coverage, known traps, licence and limits | [Datasheets](https://huggingface.co/docs/hub/model-cards) make a result interpretable as well as re-runnable | In place: [Dubai](../dubai-property/docs/DATASHEET.md), [Grid Pulse](../grid-pulse/docs/DATASHEET.md) |

**A deliberate exception:** Cookiecutter's default is to keep data out of Git, and GitHub suggests Git LFS for large files. We commit raw data so that anyone can rebuild the results from one clone. The `.git` folder is about 520 MB against [GitHub's 10 GB recommended limit](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits). Review this if it passes 1 GB or if files start changing often.

## Reproducibility

| Rule | Why | Status |
|---|---|---|
| Logic lives in `pipeline/`, not notebooks | [Source files are for repetition](https://cookiecutter-data-science.drivendata.org/opinions/) | In place |
| Exact dependency versions are locked | [Reproducing starts with the same environment](https://cookiecutter-data-science.drivendata.org/opinions/) | In place: `grid-pulse/requirements-lock.txt`, used by CI |
| One command rebuilds each project from raw data | Pipelines should re-run from code and raw data | In place for Grid Pulse: `make grid-pulse` reproduced the committed results exactly on 5 November 2026. `make dubai` rebuilds the Dubai results |
| Models record seeds, settings and accuracy by region or group | [Model cards](https://huggingface.co/docs/hub/model-cards) report results beyond one headline number | In place: [forecast model card](../grid-pulse/docs/MODEL_CARD.md) |
| Secrets never enter Git; any local secrets go in an ignored `.env` file | [Cookiecutter](https://cookiecutter-data-science.drivendata.org/opinions/) | In place: no secrets are used, and `.env` is ignored |

**Sharing the data:** raw files are public and listed in [the data index](../DATA.md). Before any new dataset goes public, its licence must be read and must allow republishing. The Dubai licence is summarised in [the data notice](../dubai-property/data/raw/README.md).

## Commits and pull requests

- **Small commits:** each commit is one real change, with a message saying what it does. No empty commits.
- **Pull requests:** each stage of work gets one. It merges only after its tests pass.
- **Pace:** at most [6 pushes a minute](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits), so scripted pushes wait at least 10 seconds between each. The first upload broke this, reaching 17 in a minute.
- **Workflow order:** a test step reaches `main` in the same pull request as, or after, the folder it tests. The first upload broke this too, as [issue 5](https://github.com/yousufagha/ai-recommendations-portfolio/issues/5) records.
- **Signing:** commits are signed. Merge commits made on GitHub carry GitHub's own signature.

## Repo health and security

| Item | Why | Status |
|---|---|---|
| README, licence | [GitHub community profile](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories) | In place |
| Secret scanning and push protection | [Blocks supported secrets on push](https://docs.github.com/en/code-security/getting-started/securing-your-repository) | In place |
| Tests on every pull request | Catches breakage before `main` | In place |
| CONTRIBUTING, code of conduct, issue templates | [Community profile](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/about-community-profiles-for-public-repositories) | In place |
| SECURITY.md | [GitHub suggests it](https://docs.github.com/en/code-security/getting-started/securing-your-repository) | In place, with private reporting on |
| Dependabot security updates | [Opens pull requests for vulnerable dependencies](https://docs.github.com/en/code-security/getting-started/securing-your-repository);  | In place |
| Branch protection requiring tests to pass on `main` | [GitHub recommends it](https://docs.github.com/en/repositories/creating-and-managing-repositories/best-practices-for-repositories) | In place: the `test` check must pass. The owner can still override it |
| Linting with ruff, run in CI | Common Python practice, not checked against a primary source today | In place |

## Claims

- Every published figure traces to a tested script or a results file.
- A public claim is checked against the data before it merges, and findings that weaken a recommendation are disclosed.
- Writing about the UAE is respectful and forward-looking, and every figure and test result is reported accurately, whichever way it goes.
- Data publishers are credited in the README, and analysis is labelled as not being financial, investment or immigration advice.
