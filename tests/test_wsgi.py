import sys
from pathlib import Path
import pytest

from autograder_gen.web import app, application
from autograder_gen.web.app import main as web_main
import autograder_gen.web.wsgi as wsgi_module


def test_wsgi_app_callable_exported():
    assert application is app
    assert wsgi_module.application is app
    assert wsgi_module.app is app


def test_wsgi_script_file_exists():
    wsgi_file = Path(__file__).parent.parent / "autograder_gen" / "web" / "wsgi" / "autograder.wsgi"
    assert wsgi_file.is_file()

    # Verify that the script can be read and parsed as valid python
    content = wsgi_file.read_text(encoding="utf-8")
    compiled = compile(content, str(wsgi_file), "exec")
    assert compiled is not None


def test_wsgi_module_target():
    import importlib

    web_mod = importlib.import_module("autograder_gen.web")
    assert hasattr(web_mod, "app")
    assert callable(getattr(web_mod, "app"))
