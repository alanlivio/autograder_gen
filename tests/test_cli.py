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
                {"target_file": "solution.py", "total_mark": 10, "type": "output_comparison"}
            ],
        }
    ],
}


def test_cli_generates_autograder(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
    )
    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    zip_path = tmp_path / "autograder.zip"
    assert zip_path.exists(), "autograder.zip was not created by the CLI"


def test_cli_generates_all_assets(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(config_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert (tmp_path / "autograder.zip").exists()
    assert not (tmp_path / "description.docx").exists()
    assert not (tmp_path / "description.md").exists()
    assert not (tmp_path / "rubric.csv").exists()
    assert (tmp_path / "stub_correct_answer.zip").exists()
    assert (tmp_path / "stub_wrong_answer.zip").exists()
    assert (tmp_path / "stub_compiler_error.zip").exists()
    assert (tmp_path / "stub_correct_answer_wrong_location.zip").exists()


def test_cli_generates_descriptions(tmp_path):
    config_path = tmp_path / "config.yaml"
    with open(config_path, "w") as f:
        json.dump(SAMPLE_CONFIG, f)
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(config_path),
            "--descriptions",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    assert (tmp_path / "autograder.zip").exists()
    assert (tmp_path / "description.docx").exists()
    assert (tmp_path / "description.md").exists()


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
    assert (Path("tests/examples/py_simple") / "submission.log").exists()


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


def test_cli_run_stubs_submissions_with_config():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            "tests/examples/py_simple/config.yaml",
            "--run-stubs-submissions",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "[AutograderRunner: Student View]" in result.stdout
    assert "submission=stub_correct_answer.zip" in result.stdout
    assert "submission=stub_wrong_answer.zip" in result.stdout
    assert "submission=stub_compiler_error.zip" in result.stdout
    assert "submission=stub_correct_answer_wrong_location.zip" in result.stdout


def test_cli_run_stubs_submissions_with_zip(tmp_path):
    cfg_src = Path("tests/examples/py_simple/config.yaml").read_text(encoding="utf-8")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(cfg_src, encoding="utf-8")
    python_executable = sys.executable
    gen_result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(cfg_file),
        ],
        capture_output=True,
        text=True,
    )
    assert gen_result.returncode == 0
    autograder_zip = tmp_path / "autograder.zip"
    assert autograder_zip.exists()

    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--config",
            str(autograder_zip),
            "--run-stubs-submissions",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "[AutograderRunner: Student View]" in result.stdout
    assert "submission=stub_correct_answer.zip" in result.stdout


def test_cli_run_stubs_submissions_direct_arg():
    python_executable = sys.executable
    result = subprocess.run(
        [
            python_executable,
            "autograder_gen/cli.py",
            "--run-stubs-submissions",
            "tests/examples/py_simple/config.yaml",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "[AutograderRunner: Student View]" in result.stdout
    assert "submission=stub_correct_answer.zip" in result.stdout
