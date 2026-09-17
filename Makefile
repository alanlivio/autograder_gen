.PHONY: help venv deps build test run-examples gen-example gen-examples serve clean format wheel publish-pypi

PYTHON ?= $(shell if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
VENV ?= .venv


help:
	@printf "%s\n" \
		"Available Makefile targets:" \
		"  venv          - Create virtual environment (.venv) and install dependencies" \
		"  deps          - Install dependencies" \
		"  build         - Build package distribution" \
		"  wheel         - Build wheel distribution and check with twine" \
		"  test          - Run pytest test suite" \
		"  run-examples  - Run examples autograders and log student view results" \
		"  gen-examples  - Generate autograder packages for tests/examples" \
		"  format        - Format Python code using black" \
		"  serve         - Start Flask web server" \
		"  clean         - Clean build and temporary files"

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
	pip install --upgrade pip
	pip install -r requirements.txt -r requirements-dev.txt

build:
	pip install --upgrade build
	python -m build

test:
	$(PYTHON) -m pytest tests

run-examples:
	PYTHONPATH=. $(PYTHON) scripts/run_autograder_for_configs_in_folder.py tests/examples

gen-examples:
	PYTHONPATH=. $(PYTHON) scripts/gen_autograder_for_configs_in_folder.py tests/examples

format:
	black .

serve:
	python autograder_gen/web/app.py

clean:
	rm -rf dist build ./*.egg-info .pytest_cache tests/examples/*/*.zip tests/examples/*/description.* tests/examples/*/rubric.*

wheel:
	$(VENV)/bin/pip install build setuptools twine
	rm -rf dist build ./*.egg-info
	$(VENV)/bin/python -m build . --wheel
	$(VENV)/bin/twine check dist/*

publish-pypi: wheel
	twine upload dist/*
