ifeq ($(OS),Windows_NT)
    PIP = .venv/Scripts/python -m pip
    PYTHON = python
else
    PIP = .venv/bin/python -m pip
    PYTHON = python3
endif

ifneq (,$(wildcard .env))
    include .env
    export
endif

.PHONY: dev_env test_deploy

dev_env:
ifeq ($(OS),Windows_NT)
	$(PYTHON) -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt -r requirements-dev.txt
	@echo "To activate the environment, run:"
	@echo "  .venv\\Scripts\\activate"
else
	$(PYTHON) -m venv .venv || python -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt -r requirements-dev.txt
	@echo "To activate the environment, run:"
	@echo "  source .venv/bin/activate"
endif



test_deploy:
ifeq ($(OS),Windows_NT)
	@echo "Error: test_deploy is only supported on Linux."
	@exit 1
else
	@uname | grep -q Linux || (echo "Error: test_deploy is only supported on Linux." && exit 1)
	[ -d /var/www ] || mkdir -p /var/www
	ln -snf $(CURDIR) /var/www/autograder
	PYTHONPATH=/var/www .venv/bin/python -c "import sys, importlib.util; from importlib.machinery import SourceFileLoader; loader=SourceFileLoader('autograder.wsgi', 'autograder.wsgi'); spec=importlib.util.spec_from_loader('autograder.wsgi', loader); mod=importlib.util.module_from_spec(spec); sys.modules['autograder.wsgi']=mod; loader.exec_module(mod); from gunicorn.app.wsgiapp import run; run()" --bind 0.0.0.0:8000 autograder.wsgi:application
endif



