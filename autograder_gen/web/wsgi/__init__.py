"""
WSGI deployment module for AutograderGen Web.
Exposes application callable for WSGI servers (Gunicorn, mod_wsgi, uWSGI).
"""

from autograder_gen.web.app import app, app as application

__all__ = ["app", "application"]
