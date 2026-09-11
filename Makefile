.PHONY: help venv deps build test serve clean format wheel publish-pypi

PYTHON ?= $(shell if [ -f .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
VENV ?= .venv


help:
	@printf "%s\n" \
		"Available Makefile targets:" \
		"  venv    - Create virtual environment (.venv) and install dependencies" \
		"  deps    - Install dependencies" \
		"  build   - Build package distribution" \
		"  wheel   - Build wheel distribution and check with twine" \
		"  test    - Run pytest test suite" \
		"  format  - Format Python code using black" \
		"  serve   - Start Flask web server" \
		"  clean   - Clean build and temporary files"

venv:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt -r requirements-dev.txt
	@echo ""
	@echo "Virtual environment created in $(VENV)."
	@echo "To activate in your terminal shell, run:"
	@echo "  source $(VENV)/bin/activate"

deps:
	pip install --upgrade pip
	pip install -r requirements.txt -r requirements-dev.txt

build:
	pip install --upgrade build
	python -m build

test:
	$(PYTHON) -m pytest tests

format:
	black .

serve:
	python autograder_gen/web/app.py

clean:
	rm -rf dist build ./*.egg-info .pytest_cache

wheel:
	$(VENV)/bin/pip install build setuptools twine
	rm -rf dist build ./*.egg-info
	$(VENV)/bin/python -m build . --wheel
	$(VENV)/bin/twine check dist/*

publish-pypi: wheel
	twine upload dist/*
