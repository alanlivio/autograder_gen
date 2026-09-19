import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
import pytest
import yaml
from pydantic import ValidationError
import autograder_gen as ag


def test_config_wrong_file_location_deduction_default():
    data = {
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
                        "type": "file_exists",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(data)
    assert cfg.wrong_file_location_deduction == 0.0
    assert cfg.get_config_summary()["wrong_file_location_deduction"] == 0.0


def test_config_wrong_file_location_deduction_custom():
    data = {
        "version": "1.0",
        "language": "python",
        "wrong_file_location_deduction": 2.5,
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "file_exists",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(data)
    assert cfg.wrong_file_location_deduction == 2.5
    assert cfg.get_config_summary()["wrong_file_location_deduction"] == 2.5


def test_config_wrong_file_location_deduction_requires_strict_false():
    data = {
        "version": "1.0",
        "language": "python",
        "strict_file_location": True,
        "wrong_file_location_deduction": 2.5,
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "file_exists",
                    }
                ],
            }
        ],
    }
    with pytest.raises(ValidationError) as exc:
        ag.Config.model_validate(data)
    assert "wrong_file_location_deduction is only supported when strict_file_location is False" in str(exc.value)


def test_config_wrong_file_location_deduction_negative_fails():
    data = {
        "version": "1.0",
        "language": "python",
        "wrong_file_location_deduction": -1.0,
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "file_exists",
                    }
                ],
            }
        ],
    }
    with pytest.raises(ValidationError) as exc:
        ag.Config.model_validate(data)
    assert "wrong_file_location_deduction must be non-negative" in str(exc.value)


def test_wrong_file_location_deduction_execution(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "strict_file_location": False,
        "wrong_file_location_deduction": 3.0,
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "File Check",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10.0,
                        "type": "file_exists",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    generator = ag.Engine(cfg, config_dict)
    gen_dir = tmp_path / "generated"
    output_zip = generator.generate(str(gen_dir))

    work_dir = tmp_path / "run"
    work_dir.mkdir()
    with zipfile.ZipFile(output_zip, "r") as z:
        z.extractall(work_dir)

    submission_dir = work_dir / "submission"
    sub_folder = submission_dir / "nested" / "dir"
    sub_folder.mkdir(parents=True)
    (sub_folder / "solution.py").write_text("print('hello')", encoding="utf-8")

    results_path = work_dir / "results.json"
    process = subprocess.run(
        [sys.executable, str(work_dir / "run_tests.py")],
        cwd=work_dir,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": str(work_dir),
            "GRADESCOPE_RESULTS_PATH": str(results_path),
            "GRADESCOPE_SOURCE_PATH": str(submission_dir),
        },
    )
    assert results_path.exists(), f"results.json not created. stderr: {process.stderr}"
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    test_res = results["tests"][0]
    assert test_res["score"] == 7.0
    assert test_res["max_score"] == 10.0


def test_wrong_file_location_deduction_not_applied_when_location_correct(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "strict_file_location": False,
        "wrong_file_location_deduction": 3.0,
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "File Check",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10.0,
                        "type": "file_exists",
                    }
                ],
            }
        ],
    }
    cfg = ag.Config.model_validate(config_dict)
    generator = ag.Engine(cfg, config_dict)
    gen_dir = tmp_path / "generated"
    output_zip = generator.generate(str(gen_dir))

    work_dir = tmp_path / "run"
    work_dir.mkdir()
    with zipfile.ZipFile(output_zip, "r") as z:
        z.extractall(work_dir)

    submission_dir = work_dir / "submission"
    submission_dir.mkdir()
    (submission_dir / "solution.py").write_text("print('hello')", encoding="utf-8")

    results_path = work_dir / "results.json"
    process = subprocess.run(
        [sys.executable, str(work_dir / "run_tests.py")],
        cwd=work_dir,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": str(work_dir),
            "GRADESCOPE_RESULTS_PATH": str(results_path),
            "GRADESCOPE_SOURCE_PATH": str(submission_dir),
        },
    )
    assert results_path.exists(), f"results.json not created. stderr: {process.stderr}"
    with open(results_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    test_res = results["tests"][0]
    assert test_res["score"] == 10.0
    assert test_res["max_score"] == 10.0
