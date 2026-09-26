import json
import subprocess
from pathlib import Path
import sys
import zipfile

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
    assert (output_dir / "compiler_error.zip").exists()
    assert (output_dir / "correct_answer_wrong_location.zip").exists()


def test_cli_missing_config():
    python_executable = sys.executable
    result = subprocess.run(
        [python_executable, "autograder_gen/cli.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0


def test_cli_run_submission_folder():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            "tests/examples/py_simple/config.yaml",
            "--run-submission",
            "tests/examples/py_simple/correct_answer",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "[AutograderRunner: Student View]" in result.stdout
    assert "Actual Score = 10" in result.stdout


def test_cli_run_submission_zip(tmp_path):
    sub_zip = tmp_path / "submission.zip"
    with zipfile.ZipFile(sub_zip, "w") as z:
        for f in Path("tests/examples/py_simple/correct_answer").iterdir():
            z.write(f, f.name)
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            "tests/examples/py_simple/config.yaml",
            "--run-submission",
            str(sub_zip),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "[AutograderRunner: Student View]" in result.stdout
    assert "Actual Score = 10" in result.stdout


def test_cli_run_submission_auto_config():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--run-submission",
            "tests/examples/py_simple/correct_answer",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "[AutograderRunner: Student View]" in result.stdout


def test_cli_run_submission_not_found():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            "tests/examples/py_simple/config.yaml",
            "--run-submission",
            "nonexistent_submission_dir",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0

