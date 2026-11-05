.PHONY: setup test lint grid-pulse

# Installs the locked versions into one environment shared by both projects
setup:
	python3 -m venv grid-pulse/.venv
	grid-pulse/.venv/bin/python -m pip install -r grid-pulse/requirements-lock.txt

test:
	cd grid-pulse && .venv/bin/python -m pytest -q
	cd dubai-property && ../grid-pulse/.venv/bin/python -m pytest -q

lint:
	grid-pulse/.venv/bin/ruff check .

# Rebuilds every Grid Pulse result from the committed raw data, then tests it
grid-pulse:
	cd grid-pulse && .venv/bin/python -m pipeline.build_star
	cd grid-pulse && .venv/bin/python -m pipeline.insights
	cd grid-pulse && .venv/bin/python -m pipeline.render_recommendations
	cd grid-pulse && .venv/bin/python -m pipeline.forecast
	cd grid-pulse && .venv/bin/python -m pipeline.export_looker
	cd grid-pulse && .venv/bin/python -m pytest -q
