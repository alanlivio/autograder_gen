import pytest
import yaml
from pathlib import Path
from pydantic import ValidationError

import autograder_gen as ag


def test_config_total_score_single_question():
    data = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Question 1",
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
    config = ag.Config.model_validate(data)
    assert config.total_score == 10


def test_config_total_score_multiple_questions_and_items():
    data = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py", "helper.py"],
        "questions": [
            {
                "name": "Question 1",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "file_exists",
                    },
                    {
                        "target_file": "solution.py",
                        "total_mark": 15,
                        "type": "function_test",
                        "function_name": "add",
                        "test_cases": [{"args": [1, 2], "expected": "3"}],
                    },
                ],
            },
            {
                "name": "Question 2",
                "marking_items": [
                    {
                        "target_file": "helper.py",
                        "total_mark": 25,
                        "type": "file_exists",
                    }
                ],
            },
        ],
    }
    config = ag.Config.model_validate(data)
    assert config.total_score == 50
    assert config.get_config_summary()["total_marks"] == 50


def test_config_total_score_from_yaml_file(tmp_path: Path):
    yaml_content = """
version: '1.0'
language: python
files_necessary:
  - solution.py
questions:
  - name: Math Tests
    marking_items:
      - target_file: solution.py
        total_mark: 12
        type: function_test
        function_name: add
        test_cases:
          - args: [1, 2]
            expected: '3'
      - target_file: solution.py
        total_mark: 8
        type: function_test
        function_name: multiply
        test_cases:
          - args: [2, 3]
            expected: '6'
"""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(yaml_content, encoding="utf-8")

    config = ag.Config.parse(cfg_file)
    assert config.total_score == 20
    assert config.get_config_summary()["total_questions"] == 1
    assert config.get_config_summary()["total_marking_items"] == 2


def test_config_missing_target_file_in_files_necessary():
    data = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["other.py"],
        "questions": [
            {
                "name": "Q1",
                "marking_items": [
                    {
                        "target_file": "missing.py",
                        "total_mark": 10,
                        "type": "file_exists",
                    }
                ],
            }
        ],
    }
    with pytest.raises(ValidationError):
        ag.Config.model_validate(data)


def test_file_exists_with_time_limit_fails_validation():
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
                        "total_mark": 0,
                        "type": "file_exists",
                        "time_limit": 5,
                    }
                ],
            }
        ],
    }
    with pytest.raises(ValidationError) as excinfo:
        ag.Config.model_validate(data)
    assert "time_limit is not allowed for type 'file_exists'" in str(excinfo.value)


def test_strict_file_location_configuration():
    base_data = {
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
    cfg_default = ag.Config.model_validate(base_data)
    assert cfg_default.strict_file_location is False

    cfg_strict = ag.Config.model_validate({**base_data, "strict_file_location": True})
    assert cfg_strict.strict_file_location is True
