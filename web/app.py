import sys
import os
from pathlib import Path

# Add project root to sys.path to allow running this script directly from the root
sys.path.append(str(Path(__file__).parent.parent))
from flask import Flask, request, send_file, jsonify, render_template
import tempfile
import zipfile
import yaml
import autograder_gen as ag
import json
from flask_cors import CORS
from flask_bootstrap import Bootstrap5
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, static_url_path="/static", static_folder="static")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-for-autograder")
bootstrap = Bootstrap5(app)
CORS(app)


@app.route("/", methods=["GET"])
def index():
    return render_template("home.html")


@app.route("/generate", methods=["GET"])
def generate():
    return render_template("index.html")


@app.route("/docs", methods=["GET"])
def documentation():
    schema_dict = ag.Config.model_json_schema()
    schema_str = json.dumps(schema_dict, indent=2)
    return render_template("docs.html", schema=schema_str)


@app.route("/upload-config", methods=["POST"])
def upload_config():
    """Handle YAML config file upload and return the parsed configuration."""
    if "config_file" not in request.files:
        return jsonify({"error": "No config file provided"}), 400
    file = request.files["config_file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    if not file.filename or not (
        file.filename.endswith(".yaml") or file.filename.endswith(".yml")
    ):
        return jsonify({"error": "File must be a YAML file (.yml or .yaml)"}), 400
    try:
        content = file.read().decode("utf-8")
        config_data = yaml.safe_load(content)
        validator = ag.Validator()
        if not validator.validate_json(config_data):
            return (
                jsonify(
                    {
                        "error": "Invalid configuration file",
                        "validation_errors": validator.get_errors(),
                    }
                ),
                400,
            )
        return jsonify(
            {
                "success": True,
                "config": config_data,
                "warnings": validator.get_warnings(),
            }
        )
    except Exception as e:
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500


@app.route("/api/export/bundle", methods=["POST"])
def export_bundle():
    """Generate all assessment assets and package them into a single all_assets.zip file."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No config data provided"}), 400
    try:
        config = ag.Config.model_validate(data)
        generator = ag.Engine(config, data)
        with tempfile.TemporaryDirectory() as out_dir:
            generator.generate(out_dir)
            out_path = Path(out_dir)
            bundle_zip_path = out_path / "all_assets.zip"
            with zipfile.ZipFile(bundle_zip_path, "w") as z:
                for f in out_path.iterdir():
                    if f.name != "all_assets.zip" and f.is_file():
                        z.write(f, f.name)
            with open(bundle_zip_path, "rb") as zf:
                bundle_data = zf.read()
            from io import BytesIO

            bundle_buffer = BytesIO(bundle_data)
            bundle_buffer.seek(0)
            return send_file(
                bundle_buffer,
                as_attachment=True,
                download_name="all_assets.zip",
                mimetype="application/zip",
            )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/validate", methods=["POST"])
def validate_config():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No config data provided"}), 400
    try:
        validator = ag.Validator()
        valid = validator.validate_json(data)
        return jsonify(
            {
                "valid": valid,
                "errors": validator.get_errors(),
                "warnings": validator.get_warnings(),
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/example/<name>", methods=["GET"])
def get_example_config(name):
    try:
        yaml_str = ag.Config.get_example_config_yaml(name)
        config_data = yaml.safe_load(yaml_str)
        return jsonify({"success": True, "config": config_data, "yaml": yaml_str})
    except Exception as e:
        return jsonify({"error": f"Error loading example: {str(e)}"}), 500


@app.route("/api/diff", methods=["POST"])
def diff_configs():
    data = request.get_json()
    if not data or "config1" not in data or "config2" not in data:
        return jsonify({"error": "Both config1 and config2 must be provided"}), 400
    try:
        cfg1 = ag.Config.model_validate(data["config1"])
        cfg2 = ag.Config.model_validate(data["config2"])
        diff_res = compare_configs(cfg1, cfg2)
        return jsonify({"success": True, "diff": diff_res})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/normalize", methods=["POST"])
def normalize_config_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No config data provided"}), 400
    try:
        normalized = ag.normalize_autograder_config(data)
        yaml_str = yaml.dump(normalized, sort_keys=False)
        return jsonify({"success": True, "normalized": normalized, "yaml": yaml_str})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/lint", methods=["POST"])
def lint_config_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No config data provided"}), 400
    try:
        report = ag.Validator.lint_config(data)
        return jsonify({"success": True, "report": report})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run the AutograderGen Web Interface")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host address to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", "-p", type=int, default=5000, help="Port to listen on (default: 5000)"
    )
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
