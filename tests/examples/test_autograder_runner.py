import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
import yaml
import autograder_gen as ag


def run_autograder_sh_scenario(
    example_name: str,
    subdir: str,
    expected_score: int,
    config_file: str = "config.yaml",
):
    base_dir = Path(__file__).parent.parent.parent
    example_dir = base_dir / "tests/examples" / example_name
    config_path = example_dir / config_file
    student_dir = example_dir / subdir

    runner = ag.AutograderRunner(config_path)
    results = runner.run_autograder_for_submission(student_dir)
    assert "tests" in results
    total_score = sum(t.get("score", 0) for t in results["tests"])
    print(
        f"[{example_name}] ({subdir}): expected score={expected_score}, actual score={total_score}"
    )
    assert total_score == expected_score


@pytest.mark.parametrize(
    "example_name, subdir, expected_score",
    [
        ("py_simple", "correct_answer", 10),
        ("py_simple", "wrong_answer", 0),
        ("py_simple", "compiler_error", 0),
        ("py_simple", "missing_file", 0),
        ("py_simple", "wrong_file_location", 10),
        ("py_function", "correct_answer", 10),
        ("py_function", "wrong_answer", 5),
        ("py_function", "compiler_error", 0),
        ("py_function", "missing_file", 0),
        ("py_function", "wrong_file_location", 10),
        ("py_complete", "correct_answer", 100),
        ("py_complete", "wrong_answer", 0),
        ("py_complete", "compiler_error", 0),
        ("py_complete", "missing_file", 0),
        ("py_complete", "wrong_file_location", 100),
        ("java_simple", "correct_answer", 10),
        ("java_simple", "wrong_answer", 0),
        ("java_simple", "compiler_error", 0),
        ("java_simple", "missing_file", 0),
        ("java_simple", "wrong_file_location", 10),
    ],
)
def test_examples_run_autograder_sh(example_name, subdir, expected_score):
    if example_name == "java_simple" and shutil.which("javac") is None:
        pytest.skip("javac is not installed")
    run_autograder_sh_scenario(example_name, subdir, expected_score)


def test_autograder_runner_config_obj(tmp_path):
    cfg_data = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "function_test",
                        "function_name": "add",
                        "test_cases": [{"args": [1, 2], "expected": "3"}],
                    }
                ],
            }
        ],
    }
    no_ext_file = tmp_path / "custom_config_file"
    no_ext_file.write_text(yaml.dump(cfg_data), encoding="utf-8")

    runner = ag.AutograderRunner(no_ext_file)
    assert runner.config_obj is not None
    assert runner.config_obj.total_score == 10


def test_run_autograder_for_generated_submissions(tmp_path):
    base_dir = Path(__file__).parent.parent.parent
    config_path = base_dir / "tests/examples/py_simple/config.yaml"
    runner = ag.AutograderRunner(config_path)

    results = runner.run_autograder_for_generated_submissions()
    assert "correct_answer" in results
    assert "wrong_answer" in results

    correct_score = sum(t.get("score", 0) for t in results["correct_answer"]["tests"])
    wrong_score = sum(t.get("score", 0) for t in results["wrong_answer"]["tests"])

    assert correct_score == 10
    assert wrong_score == 0

    assert "log_path" in results["correct_answer"]
    assert "log_path" in results["wrong_answer"]
    correct_log = Path(results["correct_answer"]["log_path"])
    wrong_log = Path(results["wrong_answer"]["log_path"])
    assert correct_log.exists()
    assert wrong_log.exists()
    assert correct_log.name == "config_correct_answer.log"
    assert wrong_log.name == "config_wrong_answer.log"
    assert "# Total Score = 10, Actual Score = 10" in correct_log.read_text(encoding="utf-8")
    assert "# Total Score = 10, Actual Score = 0" in wrong_log.read_text(encoding="utf-8")

    correct_text = correct_log.read_text(encoding="utf-8")
    wrong_text = wrong_log.read_text(encoding="utf-8")
    assert "[AutograderRunner Summary]" not in correct_text
    assert "Status =" not in correct_text
    assert "[AutograderRunner Summary]" not in wrong_text
    assert "Status =" not in wrong_text
