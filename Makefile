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
