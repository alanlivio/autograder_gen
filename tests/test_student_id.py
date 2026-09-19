import json
import zipfile
from pathlib import Path
import pytest
import autograder_gen as ag
from autograder_gen.grader_utils import get_student_id


def test_config_retrieve_student_id_default():
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
    assert cfg.retrieve_student_id is False
    assert cfg.get_config_summary()["retrieve_student_id"] is False


def test_config_retrieve_student_id_enabled():
    data = {
        "version": "1.0",
        "language": "python",
        "retrieve_student_id": True,
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
    assert cfg.retrieve_student_id is True
    assert cfg.get_config_summary()["retrieve_student_id"] is True


def test_get_student_id_from_metadata(tmp_path: Path):
    meta = {
        "users": [
            {
                "sid": "33931382",
                "email": "a.guedes@reading.ac.uk",
            }
        ]
    }
    meta_path = tmp_path / "submission_metadata.json"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    result = get_student_id(autograder_root=tmp_path)
    assert result == "33931382"


def test_get_student_id_strip_non_digits(tmp_path: Path):
    meta = {
        "users": [
            {
                "sid": "ID-33931382",
                "email": "student@reading.ac.uk",
            }
        ]
    }
    meta_path = tmp_path / "submission_metadata.json"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    result = get_student_id(autograder_root=tmp_path)
    assert result == "33931382"


def test_get_student_id_fallback_to_classlist(tmp_path: Path):
    meta = {
        "users": [
            {
                "sid": "",
                "email": "c.anstee@student.reading.ac.uk",
            }
        ]
    }
    meta_path = tmp_path / "submission_metadata.json"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    classlist_file = tmp_path / "classlist.csv"
    classlist_file.write_text(
        "SPR code,Email address\n33931382,a.guedes@reading.ac.uk\n31018601,c.anstee@student.reading.ac.uk\n",
        encoding="utf-8",
    )

    result = get_student_id(autograder_root=tmp_path, classlist_path=classlist_file)
    assert result == "31018601"


def test_get_student_id_default_fallback(tmp_path: Path):
    meta = {
        "users": [
            {
                "sid": "",
                "email": "unknown@student.reading.ac.uk",
            }
        ]
    }
    meta_path = tmp_path / "submission_metadata.json"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    result = get_student_id(autograder_root=tmp_path)
    assert result == "12345678"


def test_generator_output_with_retrieve_student_id(tmp_path: Path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "retrieve_student_id": True,
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Check File",
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
    cfg = ag.Config.model_validate(config_dict)
    engine = ag.Engine(cfg, config_dict)
    out_dir = tmp_path / "out"
    zip_path = engine.generate(str(out_dir))

    with zipfile.ZipFile(zip_path, "r") as z:
        test_py = z.read("tests/question_1_test.py").decode("utf-8")
        assert "get_student_id" in test_py
        assert "self.student_id = get_student_id()" in test_py
        assert 'os.environ["STUDENT_ID"] = self.student_id' in test_py

        run_tests_py = z.read("run_tests.py").decode("utf-8")
        assert 'os.environ["STUDENT_ID"] = get_student_id()' in run_tests_py

        run_autograder = z.read("run_autograder").decode("utf-8")
        assert 'cp "classlist.csv"' in run_autograder
