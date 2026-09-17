import json
import os
import shutil
import tempfile
import zipfile
import pytest
from pydantic import ValidationError

import autograder_gen as ag
from autograder_gen.grader_utils import StudentMessage


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
    assert config.total_score == 10

    validator = ag.Validator()
    assert validator.validate_from_file(str(yaml_path)) is True


def test_template_generation_gitlab(tmp_path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "questions": [
            {
                "name": "Question 1",
                "marking_items": [
                    {
                        "total_mark": 5,
                        "type": "gitlab_submission_exists",
                        "name": "verify_git_submission",
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
        assert "grader_utils.py" in z.namelist()
        test_content = z.read("tests/question_1_test.py").decode("utf-8")

        assert "def test_verify_git_submission(self):" in test_content
        assert 'print(f"# 1.1) verify_git_submission")' in test_content
        assert "submission_metadata.json" in test_content
        assert "StudentMessage.WRONG_GITLAB_NOT_USED" in test_content
        assert "GitLab" in test_content


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
