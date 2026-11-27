.PHONY: install lint test receipts fixture report evidence diagram verify clean

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check .
	python tools/check_no_emdash.py

# Tests run as their own step and write the machine-readable reports the metrics
# collector reads, so a red test surfaces here rather than as a traceback from a
# metrics script (references/ci-and-rendering-traps.md, trap 4).
test:
	python -m pytest -q --junitxml=junit.xml --cov=flowmetrics --cov-branch \
		--cov-report=xml:coverage.xml --cov-report=json --cov-report=term-missing

receipts:
	python tools/collect_metrics.py --skip-tests
	python tools/check_numbers.py

fixture:
	python -m flowmetrics.cli fixture --scenario capacity_drop
	python -m flowmetrics.cli fixture --scenario steady --out data/events_steady.csv
	python -m flowmetrics.cli fixture --scenario transient_burst --out data/events_burst.csv

report:
	python -m flowmetrics.cli report

diagram:
	python tools/render_diagram.py

# Evidence needs the optional browser tooling: pip install -e ".[evidence]".
evidence: report diagram
	python tools/capture_screenshots.py
	python tools/record_demo.py

verify: lint test receipts
	@echo "verify: lint, tests and receipts all passed"

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ */__pycache__ \
		junit.xml coverage.json coverage.xml .coverage \
		docs/report.html docs/report.pdf docs/metrics.json
