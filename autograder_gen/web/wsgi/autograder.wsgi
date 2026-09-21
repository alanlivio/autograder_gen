#!/usr/bin/env python3
"""
WSGI entry point script for Apache mod_wsgi, uWSGI, or Gunicorn.
When autograder_gen is installed via pip, the application callable
is loaded directly from the package environment.
"""

import logging
import sys
from pathlib import Path

# Optional: if running under /var/www/autograder/ with local symlink or virtualenv
dev_link = Path("/var/www/autograder/autograder")
if dev_link.exists() and str(dev_link) not in sys.path:
    sys.path.insert(0, str(dev_link))

venv_site = Path("/var/www/autograder/venv/lib")
if venv_site.exists():
    for p in venv_site.glob("python*/site-packages"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))

from autograder_gen.web.app import app as application

logging.basicConfig(stream=sys.stderr)

if __name__ == "__main__":
    application.run()
