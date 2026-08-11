import pytest
import os
import json
import yaml
from inspect import getsourcefile
from pathlib import Path

from web.app import app


def get_examples_dir():
    current_file = getsourcefile(lambda: 0)
    if current_file is None:
        raise RuntimeError("Cannot determine current file path")
    return Path(current_file).resolve().parent


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def load_example(example_name, ext):
    dir_path = get_examples_dir() / example_name
    file_path = dir_path / f"config.{ext}"
    if not file_path.exists():
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        if ext == "json":
            return json.load(f)
        else:
            return yaml.safe_load(f)


@pytest.mark.parametrize(
    "example_name", ["py_complete", "py_function", "py_simple", "java_simple"]
)
@pytest.mark.parametrize("ext", ["json", "yaml"])
def test_web_api_validate_examples(client, example_name, ext):
    config_data = load_example(example_name, ext)
    if not config_data:
        pytest.skip(f"No {ext} config for {example_name}")

    response = client.post("/api/validate", json=config_data)
    assert response.status_code == 200

    data = response.get_json()
    assert (
        data["valid"] is True
    ), f"Validation failed for {example_name} ({ext}): {data.get('errors')}"


@pytest.mark.parametrize(
    "example_name", ["py_complete", "py_function", "py_simple", "java_simple"]
)
@pytest.mark.parametrize("ext", ["json", "yaml"])
def test_web_export_bundle_examples(client, example_name, ext):
    config_data = load_example(example_name, ext)
    if not config_data:
        pytest.skip(f"No {ext} config for {example_name}")

    response = client.post("/api/export/bundle", json=config_data)
    assert response.status_code == 200
    assert response.mimetype == "application/zip"
    assert response.data.startswith(b"PK\x03\x04")
