import json
import os
import shutil
import tempfile
import zipfile
import pytest
from pydantic import ValidationError

import autograder_gen as ag
from autograder_gen.utils import normalize


def test_normalize_function():
    assert normalize("hello  \r\nworld   \r\n") == "hello\nworld"
    assert normalize("  \n  test  \t  \n \n ") == "  test"
    assert normalize(None) == ""
    assert normalize("") == ""


def test_marking_item_gitlab_submission_exists_without_target_file():
    data = {
        "total_mark": 5,
        "type": "gitlab_submission_exists",
        "name": "Check GitLab Submission",
    }
    item = ag.MarkingItem(**data)
    assert item.type == "gitlab_submission_exists"
    assert item.target_file == ""
    assert item.total_mark == 5


def test_marking_item_github_submission_exists_without_target_file():
    data = {
        "total_mark": 5,
        "type": "github_submission_exists",
        "name": "Check GitHub Submission",
    }
    item = ag.MarkingItem(**data)
    assert item.type == "github_submission_exists"
    assert item.target_file == ""
    assert item.total_mark == 5


def test_marking_item_target_file_required_for_other_types():
    data = {
        "total_mark": 5,
        "type": "file_exists",
    }
    with pytest.raises(ValidationError) as excinfo:
        ag.MarkingItem(**data)
    assert "target_file is required" in str(excinfo.value)


def test_config_with_gitlab_submission_exists_yaml(tmp_path):
    import yaml
    config_dict = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Question 1",
                "marking_items": [
                    {
                        "total_mark": 5,
                        "type": "gitlab_submission_exists",
                        "name": "verify_gitlab_repo",
                    },
                    {
                        "total_mark": 5,
                        "type": "github_submission_exists",
                        "name": "verify_github_repo",
                    },
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "name": "check_output",
                        "expected_output": "42",
                    },
                ],
            }
        ],
    }
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(yaml.dump(config_dict), encoding="utf-8")

    config = ag.Config.parse(yaml_path)
    assert config.language == "python"
    assert len(config.questions) == 1
    assert config.questions[0].marking_items[0].type == "gitlab_submission_exists"
    assert config.questions[0].marking_items[1].type == "github_submission_exists"

    validator = ag.Validator()
    assert validator.validate_from_file(str(yaml_path)) is True


def test_template_generation_contains_new_formatting_and_gitlab(tmp_path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Question 1",
                "marking_items": [
                    {
                        "total_mark": 5,
                        "type": "gitlab_submission_exists",
                        "name": "verify_git_submission",
                    },
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "output_comparison",
                        "name": "output_test",
                        "expected_output": "42",
                    },
                ],
            }
        ],
    }
    config = ag.Config.model_validate(config_dict)
    generator = ag.Engine(config, config_dict)
    output_dir = tmp_path / "output"
    zip_path = generator.generate(str(output_dir))

    with zipfile.ZipFile(zip_path, "r") as z:
        test_content = z.read("tests/question_1_test.py").decode("utf-8")

        assert "def normalize(s: str) -> str:" in test_content
        assert 'RUNTIME_ERROR = "[RUNTIME ERROR]"' in test_content
        assert 'COMPILER_ERROR = "[COMPILER ERROR]"' in test_content
        assert 'TIME_LIMIT_EXCEEDED = "[TIME LIMITED EXCEEDED]"' in test_content
        assert 'CORRECT_ANSWER = "[CORRECT ANSWER]"' in test_content
        assert 'WRONG_ANSWER = "[WRONG ANSWER]"' in test_content

        assert "def test_verify_git_submission(self):" in test_content
        assert "submission_metadata.json" in test_content
        assert "A GitLab repository was not used in the submission." in test_content
        assert "GitLab" in test_content

        assert "def test_output_test(self):" in test_content
        assert "{COMPILER_ERROR}" in test_content
        assert "{TIME_LIMIT_EXCEEDED}" in test_content
        assert "{RUNTIME_ERROR}" in test_content
        assert "{CORRECT_ANSWER}" in test_content
        assert "{WRONG_ANSWER}" in test_content
        assert "expected_out = normalize(expected_output)" in test_content
        assert "actual_out = normalize(result.stdout)" in test_content


def test_gitlab_submission_execution_logic(tmp_path):
    metadata_file = tmp_path / "submission_metadata.json"
    
    metadata_file.write_text(json.dumps({"submission_method": "GitLab"}), encoding="utf-8")
    with metadata_file.open(encoding="utf-8") as f:
        metadata = json.load(f)
    assert metadata.get("submission_method") == "GitLab"

    metadata_file.write_text(json.dumps({"submission_method": "GitHub"}), encoding="utf-8")
    with metadata_file.open(encoding="utf-8") as f:
        metadata = json.load(f)
    assert metadata.get("submission_method") == "GitHub"

    metadata_file.write_text(json.dumps({"submission_method": "Upload"}), encoding="utf-8")
    with metadata_file.open(encoding="utf-8") as f:
        metadata = json.load(f)
    assert metadata.get("submission_method") not in ("GitLab", "GitHub")


def test_function_test_template_expected_actual_output(tmp_path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Math Test",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "function_test",
                        "function_name": "add",
                        "test_cases": [
                            {"args": [1, 2], "expected": "3"},
                        ],
                    }
                ],
            }
        ],
    }
    config = ag.Config.model_validate(config_dict)
    generator = ag.Engine(config, config_dict)
    output_dir = tmp_path / "output_fn"
    zip_path = generator.generate(str(output_dir))

    with zipfile.ZipFile(zip_path, "r") as z:
        test_content = z.read("tests/question_1_test.py").decode("utf-8")
        assert 'expected_out = normalize("3")' in test_content
        assert "actual_out = normalize(str(result))" in test_content
        assert 'print(f"Expected output:\\n{expected_out}")' in test_content
        assert 'print(f"Actual output:\\n{actual_out}")' in test_content
        assert "{WRONG_ANSWER} Output mismatch" in test_content
