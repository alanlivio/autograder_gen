.DEFAULT_GOAL := help

ifeq ($(OS),Windows_NT)
    PIP = ../.venv/Scripts/python -m pip
    PYTHON = python
else
    PIP = ../.venv/bin/python -m pip
    PYTHON = python3
endif

ifneq (,$(wildcard ../.env))
    include ../.env
    export
endif

.PHONY: help dev_env dev_deploy apache_show_error apache_prep serve

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  dev_env            Set up the virtual environment and install dependencies"
	@echo "  serve              Deploy and start the web server (Linux/WSL only)"

dev_env:
ifeq ($(OS),Windows_NT)
	$(PYTHON) -m venv ../.venv
	$(PIP) install --upgrade pip
	$(PIP) install -r ../requirements.txt -r ../requirements-dev.txt
	@echo "To activate the environment, run:"
	@echo "  .venv\\Scripts\\activate"
else
	$(PYTHON) -m venv ../.venv || python -m venv ../.venv
	$(PIP) install --upgrade pip
	$(PIP) install -r ../requirements.txt -r ../requirements-dev.txt
	@echo "To activate the environment, run:"
	@echo "  source .venv/bin/activate"
endif

apache_show_error:
	cat /var/log/apache2/autograder-error.log

apache_prep:
	ln -snf $(CURDIR)/../requirements.txt /var/www/autograder/requirements.txt
	ln -snf $(CURDIR)/static /var/www/autograder/static
	ln -snf $(CURDIR)/wsgi/autograder.wsgi /var/www/autograder/autograder.wsgi
	ln -snf $(CURDIR)/.. /var/www/autograder/autograder
	@if [ ! -d /var/www/autograder/venv ]; then \
		python3 -m venv /var/www/autograder/venv; \
		/var/www/autograder/venv/bin/pip install --upgrade pip; \
		/var/www/autograder/venv/bin/pip install -r /var/www/autograder/requirements.txt; \
	fi

serve:
ifeq ($(OS),Windows_NT)
	@echo "Error: This target must be run under Linux/WSL"
	@exit 1
else
	[ -d /var/www/autograder ] || sudo mkdir -p /var/www/autograder
	sudo chown -R $$(id -u):$$(id -g) /var/www/autograder
	$(MAKE) apache_prep
	PYTHONPATH=/var/www/autograder $(CURDIR)/../.venv/bin/python $(CURDIR)/wsgi/run_dev_wsgi.py
endif
