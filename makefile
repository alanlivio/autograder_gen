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

.PHONY: dev_env dev_deploy wsgi_links

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

dev_deploy:
	$(if $(filter Windows_NT,$(OS)),@echo "Error: only supported on Linux" && exit 1)
	[ -d /var/www/autograder ] || sudo mkdir -p /var/www/autograder
	sudo make wsgi_links
	PYTHONPATH=/var/www/autograder .venv/bin/python $(CURDIR)/web/wsgi/run_dev_wsgi.py

wsgi_links:
	$(if $(filter Windows_NT,$(OS)),@echo "Error: only supported on Linux" && exit 1)
	ln -snf $(CURDIR)/requirements.txt /var/www/autograder/requirements.txt
	ln -snf $(CURDIR)/web/static /var/www/autograder/static
	ln -snf $(CURDIR)/web/wsgi/autograder.wsgi /var/www/autograder/autograder.wsgi
	ln -snf $(CURDIR) /var/www/autograder/autograder




