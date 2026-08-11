import yaml
import pytest
import autograder_gen as ag
from autograder_gen.web.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"What is AutograderGen?" in response.data


def test_docs_route(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert b"Configuration Schema Explorer" in response.data


def test_generate_route(client):
    response = client.get("/generate")
    assert response.status_code == 200
    assert b"AutograderGen" in response.data


def test_api_validate_missing_data(client):
    response = client.post("/api/validate", json={})
    assert response.status_code == 400
    assert b"No config data provided" in response.data


def test_api_export_bundle_missing_data(client):
    response = client.post("/api/export/bundle", json={})
    assert response.status_code == 400
    assert b"No config data provided" in response.data


@pytest.mark.parametrize(
    "template_name", ["py_simple", "py_function", "py_complete", "java_simple"]
)
def test_web_app_import_and_export_all_templates(client, template_name):
    # 1. Fetch template via web API example endpoint (launch/import at start)
    example_resp = client.get(f"/api/example/{template_name}")
    assert example_resp.status_code == 200
    example_data = example_resp.get_json()
    assert example_data["success"] is True
    config_dict = example_data["config"]

    # 2. Validate configuration
    val_resp = client.post("/api/validate", json=config_dict)
    assert val_resp.status_code == 200
    assert val_resp.get_json()["valid"] is True

    # 3. Export bundle zip
    export_resp = client.post("/api/export/bundle", json=config_dict)
    assert export_resp.status_code == 200
    assert export_resp.headers["Content-Type"] == "application/zip"
    assert export_resp.data.startswith(b"PK\x03\x04")

