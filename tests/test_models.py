import pytest
from pydantic import ValidationError
import autograder_gen as ag


def test_marking_item_schema_valid():
    data = {"target_file": "solution.py", "total_mark": 10, "type": "file_exists"}
    result = ag.MarkingItem(**data)
    assert result.target_file == "solution.py"
    assert result.total_mark == 10
    assert result.type == "file_exists"
    assert result.time_limit == 30  # Default


def test_marking_item_schema_invalid_type():
    data = {"target_file": "solution.py", "total_mark": 10, "type": "invalid_type"}
    with pytest.raises(ValidationError) as excinfo:
        ag.MarkingItem(**data)
    # Check that the invalid_type triggered the validation error for 'type'
    errors = excinfo.value.errors()
    assert any(error["loc"] == ("type",) for error in errors)


def test_question_schema_valid():
    data = {
        "name": "Q1",
        "marking_items": [
            {"target_file": "solution.py", "total_mark": 10, "type": "file_exists"}
        ],
    }
    result = ag.Question(**data)
    assert result.name == "Q1"
    assert len(result.marking_items) == 1


def test_autograder_config_schema_full():
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
    result = ag.Config(**data)
    assert result.version == "1.0"
    assert result.language == "python"
    assert len(result.questions) == 1


def test_get_example_config_yaml_python():
    yaml_str = ag.Config.get_example_config_yaml("py_simple")
    assert "language: python" in yaml_str


def test_get_example_config_yaml_java():
    yaml_str = ag.Config.get_example_config_yaml("java_simple")
    assert "language: java" in yaml_str


def test_validator_and_utility_functions():
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
                        "name": "check_exists",
                    }
                ],
            }
        ],
    }
    validator = ag.Validator()
    assert validator.validate_json(data) is True

    lint_res = ag.Validator.lint_config(data)
    assert lint_res["valid"] is True
