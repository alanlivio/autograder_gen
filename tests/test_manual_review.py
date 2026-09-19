import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
import pytest
import autograder_gen as ag


def test_question_manual_review_defaults():
    q = ag.Question(
        name="Report",
        marking_items=[
            ag.MarkingItem(
                name="Check PDF",
                total_mark=15.0,
                type="manual_review",
                target_file="report.pdf",
            )
        ],
    )
    assert q.manual_review is False
    assert len(q.marking_items) == 1
    assert q.marking_items[0].type == "manual_review"


def test_question_manual_review_flag_auto_populates_items():
    data = {
        "name": "Coursework Report",
        "manual_review": True,
        "total_mark": 20.0,
        "target_file": "report.pdf",
    }
    q = ag.Question.model_validate(data)
    assert q.manual_review is True
    assert len(q.marking_items) == 1
    assert q.marking_items[0].type == "manual_review"
    assert q.marking_items[0].total_mark == 20.0
    assert q.marking_items[0].target_file == "report.pdf"


def test_question_manual_review_flag_defaults_item_type():
    data = {
        "name": "Coursework Report",
        "manual_review": True,
        "marking_items": [
            {
                "total_mark": 15.0,
                "target_file": "report.pdf",
            }
        ],
    }
    q = ag.Question.model_validate(data)
    assert q.manual_review is True
    assert q.marking_items[0].type == "manual_review"


def test_manual_review_execution_file_present(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "required_files": ["report.pdf"],
        "questions": [
            {
                "name": "Report Question",
                "manual_review": True,
                "marking_items": [
                    {
                        "name": "Written Report PDF",
                        "total_mark": 15.0,
                        "type": "manual_review",
                        "target_file": "report.pdf",
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
    (submission_dir / "report.pdf").write_bytes(b"%PDF-1.4 test")

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
    assert test_res["score"] == 0.0
    assert test_res["max_score"] == 15.0
    assert "[MANUAL_REVIEW]" in test_res["output"]


def test_manual_review_execution_file_missing(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "required_files": ["report.pdf"],
        "questions": [
            {
                "name": "Report Question",
                "manual_review": True,
                "marking_items": [
                    {
                        "name": "Written Report PDF",
                        "total_mark": 15.0,
                        "type": "manual_review",
                        "target_file": "report.pdf",
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
    assert test_res["score"] == 0.0
    assert test_res["max_score"] == 15.0
    assert "[WRONG_FILE]" in test_res["output"]


def test_manual_review_execution_no_target_file(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "questions": [
            {
                "name": "Oral Interview",
                "manual_review": True,
                "marking_items": [
                    {
                        "name": "Presentation Assessment",
                        "total_mark": 10.0,
                        "type": "manual_review",
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
    assert test_res["score"] == 0.0
    assert test_res["max_score"] == 10.0
    assert "[MANUAL_REVIEW]" in test_res["output"]


def test_manual_review_cw2_config(tmp_path: Path):
    cw2_config_path = (
        Path(__file__).parent.parent
        / ".data"
        / "assessment_cw2_config"
        / "config.yml"
    )
    assert cw2_config_path.exists()
    import yaml

    with open(cw2_config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    cfg = ag.Config.model_validate(data)
    assert cfg.total_score == 100.0
    assert cfg.questions[0].marking_items[2].type == "manual_review"
    assert cfg.questions[0].marking_items[2].total_mark == 15.0

    generator = ag.Engine(cfg, data)
    gen_dir = tmp_path / "generated"
    output_zip = generator.generate(str(gen_dir))

    work_dir = tmp_path / "run"
    work_dir.mkdir()
    with zipfile.ZipFile(output_zip, "r") as z:
        z.extractall(work_dir)

    test_q0 = (work_dir / "tests" / "question_1_test.py").read_text(
        encoding="utf-8"
    )
    assert "[MANUAL_REVIEW]" in test_q0
    assert "coursework2/SortComparison.pdf" in test_q0
