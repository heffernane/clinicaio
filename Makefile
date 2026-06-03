POETRY ?= poetry

.PHONY: check.lock
check.lock:
	@$(POETRY) check --lock

.PHONY: install
install: check.lock
	@$(POETRY) install

.PHONY: test
test: install
	@$(POETRY) run python -m pytest -v tests/unittests

.PHONY: clean.doc
clean.doc:
	@$(RM) -rf docs/_build

.PHONY: doc
doc: clean.doc install.doc
	@$(POETRY) run sphinx-build --nitpicky -b html docs docs/_build

.PHONY: install.doc
install.doc: check.lock
	@$(POETRY) install --only docs

.PHONY: notebooks
notebooks: install
	@$(POETRY) run jupyter lab notebooks/

.PHONY: typecheck
typecheck: install
	@$(POETRY) run mypy --strict