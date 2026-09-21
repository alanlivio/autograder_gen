#!/usr/bin/env python3
"""
Development WSGI runner using Gunicorn.
Runs the WSGI application callable directly from the installed package.
"""

import os
import sys
from pathlib import Path
from gunicorn.app.wsgiapp import run

# Prefer /var/www/autograder/autograder.wsgi if it exists; otherwise use package module
wsgi_file = Path("/var/www/autograder/autograder.wsgi")
if not wsgi_file.exists():
    wsgi_file = Path(__file__).resolve().parent / "autograder.wsgi"

if __name__ == "__main__":
    bind_addr = os.environ.get("AUTOGRADER_BIND", "127.0.0.1:8000")
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        bind_addr = sys.argv.pop(1)

    sys.argv = [
        sys.argv[0],
        "--bind",
        bind_addr,
        "autograder_gen.web.app:app",
    ]
    run()
