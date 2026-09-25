MAKEFLAGS += -s --no-print-directory
.DEFAULT_GOAL := help

.PHONY: help venv deps build wheel publish-pypi test run-examples gen-examples serve clean format

PYTHON ?= $(shell if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
VENV ?= .venv

help:
	@printf "%s\n" \
		"Usage: make [target]" \
		"" \
		"Targets:" \
		"  deps          Install dependencies" \
		"  test          Run pytest test suite" \
		"  pip         Build wheel distribution and check with twine" \
		"  build         Build package distribution (sdist and wheel)" \
		"  publish-pypi  Build wheel and upload to PyPI" \
		"  venv          Create virtual environment (.venv) and install dependencies" \
		"  run-examples  Run examples autograders and log student view results" \
		"  gen-examples  Generate autograder packages for tests/examples" \
		"  format        Format Python code using black" \
		"  serve         Start Flask web server" \
		"  clean         Clean build and temporary files"

venv:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt -r requirements-dev.txt
	@printf "%s\n" \
		"" \
		"Virtual environment created in $(VENV)." \
		"To activate in your terminal shell, run:" \
		"  source $(VENV)/bin/activate"

deps:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt -r requirements-dev.txt

wheel:
	$(PYTHON) -m pip install --upgrade build wheel setuptools twine
	rm -rf dist build ./*.egg-info
	$(PYTHON) -m build --wheel
	$(PYTHON) -m twine check dist/*

build:
	$(PYTHON) -m pip install --upgrade build wheel setuptools
	rm -rf dist build ./*.egg-info
	$(PYTHON) -m build

publish-pypi: wheel
	$(PYTHON) -m twine upload dist/*

test:
	$(PYTHON) -m pytest tests

run-examples:
	PYTHONPATH=. $(PYTHON) -m autograder_gen.batch_run tests/examples

gen-examples:
	PYTHONPATH=. $(PYTHON) -m autograder_gen.batch_gen tests/examples


serve:
	$(PYTHON) autograder_gen/web/app.py

clean:
	rm -rf dist build ./*.egg-info .pytest_cache tests/examples/*/*.zip tests/examples/*/description.* tests/examples/*/rubric.*
