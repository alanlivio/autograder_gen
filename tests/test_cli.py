import json
import subprocess
from pathlib import Path
import sys

SAMPLE_CONFIG = {
    "version": "1.0",
    "language": "python",
    "files_necessary": ["solution.py"],
    "questions": [
        {
            "name": "Q1",
            "marking_items": [
                {"target_file": "solution.py", "total_mark": 10, "type": "file_exists"}
            ],
        }
    ],
}


def test_cli_generates_autograder(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(config_path),
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
    )
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    zip_path = output_dir / "autograder.zip"
    assert zip_path.exists(), "autograder.zip was not created by the CLI"


def test_cli_generates_all_assets(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    output_dir = tmp_path / "output_all"
    output_dir.mkdir()
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(config_path),
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
    )
    # Check exit code
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    # Check all assets exist
    assert (output_dir / "autograder.zip").exists()
    assert (output_dir / "description.docx").exists()
    assert (output_dir / "description.md").exists()
    assert (output_dir / "rubric.csv").exists()
    assert (output_dir / "correct_answer.zip").exists()
    assert (output_dir / "wrong_answer.zip").exists()


def test_cli_example(tmp_path):
    output_dir = tmp_path / "out_example"
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--example",
            "py_simple",
            "--output",
            str(output_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI example failed: {result.stderr}"
    generated_yaml = output_dir / "py_simple.yaml"
    assert generated_yaml.exists()
    content = generated_yaml.read_text(encoding="utf-8")
    assert "language: python" in content
    conflict_result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--example",
            "py_simple",
            "--config",
            "some_config.yaml",
        ],
        capture_output=True,
        text=True,
    )
    assert conflict_result.returncode != 0
