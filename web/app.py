import sys
import os
from pathlib import Path

# Add project root to sys.path to allow running this script directly from the root
sys.path.append(str(Path(__file__).parent.parent))

from flask import Flask, request, send_file, jsonify, render_template
import tempfile
import os
import yaml
from autograder_gen.config import ConfigParser, AutograderConfig
from autograder_gen.generator import AutograderGenerator
from autograder_gen.validator import ConfigValidator
import json
from flask_cors import CORS
from flask_bootstrap import Bootstrap5
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_url_path="/static", static_folder="static")
# Get SECRET_KEY from environment or fallback to a default for development
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-for-autograder")
bootstrap = Bootstrap5(app)

CORS(app)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/docs", methods=["GET"])
def documentation():
    return render_template("docs.html")


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
        # Read and parse the YAML content
        content = file.read().decode("utf-8")
        config_data = yaml.safe_load(content)

        # Validate the configuration
        validator = ConfigValidator()
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


@app.route("/api/generate", methods=["POST"])
def generate_autograder():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No config data provided"}), 400
    tmp_path = None
    try:
        # Write config to a temp file
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".yml") as tmp:
            yaml.dump(data, tmp)
            tmp_path = tmp.name
        # Parse and validate config
        config_parser = ConfigParser(tmp_path)
        config: AutograderConfig = config_parser.parse()
        generator = AutograderGenerator(config, data)  # Pass original config dict
        with tempfile.TemporaryDirectory() as out_dir:
            zip_path = generator.generate(out_dir)
            # Read the file into memory before sending to avoid file locking issues
            with open(zip_path, "rb") as zip_file:
                zip_data = zip_file.read()
            # Create a BytesIO object to send the file data
            from io import BytesIO

            zip_buffer = BytesIO(zip_data)
            zip_buffer.seek(0)
            return send_file(
                zip_buffer,
                as_attachment=True,
                download_name="autograder.zip",
                mimetype="application/zip",
            )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if tmp_path is not None and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


@app.route("/api/export/description", methods=["POST"])
def export_description():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No config data provided"}), 400
    try:
        config = AutograderConfig.model_validate(data)
        generator = AutograderGenerator(config)
        buffer = generator.generate_description_docx()
        return send_file(
            buffer,
            as_attachment=True,
            download_name="description.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/correct", methods=["POST"])
def export_correct():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No config data provided"}), 400
    try:
        config = AutograderConfig.model_validate(data)
        generator = AutograderGenerator(config)
        buffer = generator.generate_correct_answer_zip()
        return send_file(
            buffer,
            as_attachment=True,
            download_name="correct_answer.zip",
            mimetype="application/zip",
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export/wrong", methods=["POST"])
def export_wrong():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No config data provided"}), 400
    try:
        config = AutograderConfig.model_validate(data)
        generator = AutograderGenerator(config)
        buffer = generator.generate_wrong_answer_zip()
        return send_file(
            buffer,
            as_attachment=True,
            download_name="wrong_answer.zip",
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
        validator = ConfigValidator()
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


@app.route("/api/example/py_simple", methods=["GET"])
def get_example_config():
    """Return the py_simple example YAML configuration."""
    example_path = Path(__file__).parent.parent / "tests" / "examples" / "py_simple" / "config.yaml"
    try:
        with open(example_path, "r", encoding="utf-8") as f:
            content = f.read()
            config_data = yaml.safe_load(content)
        return jsonify({"success": True, "config": config_data})
    except Exception as e:
        return jsonify({"error": f"Error loading example: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)
