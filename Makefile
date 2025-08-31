.PHONY: ci lint type test
ci: lint type test
lint:
	ruff check .
type:
	mypy .
test:
	pytest

integration:
	pytest -q tests/integration

.PHONY: reports
reports:
	@mkdir -p reports/integration
	@echo "▶ running minimal pipeline to produce FCPXML"
	@pytest -q tests/integration/test_pipeline_minimal.py --maxfail=1
	@echo "▶ generating per-file shape reports"
	@pytest -q tests/integration/test_end_to_end.py::test_fcpxml_shape_report_all --maxfail=1
	@echo "▶ building aggregated index"
	@pytest -q tests/integration/test_reports_index.py --maxfail=1
	@echo "✔ reports written to reports/integration"
