.PHONY: help venv deps build test serve clean

PYTHON ?= python3
VENV ?= .venv

help:
	@echo "Available Makefile targets:"
	@echo "  venv    - Create virtual environment (.venv) and install dependencies"
	@echo "  deps    - Install dependencies"
	@echo "  build   - Build package distribution"
	@echo "  test    - Run pytest test suite"
	@echo "  serve   - Start Flask web server"
	@echo "  clean   - Clean build and temporary files"

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
	python -m pytest

serve:
	python web/app.py

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache/ __pycache__/ autograder_gen/__pycache__/ tests/__pycache__/ output/
	find . -type d -name "__pycache__" -exec rm -rf {} +