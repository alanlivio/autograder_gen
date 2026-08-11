import pytest
from pydantic import ValidationError
import autograder_gen as ag


def test_language_validation():

    # Valid languages
    ag.Config.model_validate(
        {
            "version": "1.0",
            "language": "python",
            "files_necessary": ["t.py"],
            "questions": [
                {
                    "name": "Q1",
                    "marking_items": [
                        {"target_file": "t.py", "total_mark": 1, "type": "file_exists"}
                    ],
                }
            ],
        }
    )
    ag.Config.model_validate(
        {
            "version": "1.0",
            "language": "java",
            "files_necessary": ["t.py"],
            "questions": [
                {
                    "name": "Q1",
                    "marking_items": [
                        {"target_file": "t.py", "total_mark": 1, "type": "file_exists"}
                    ],
                }
            ],
        }
    )

    # Invalid language
    with pytest.raises(ValidationError) as excinfo:
        ag.Config.model_validate(
            {
                "version": "1.0",
                "language": "r",
                "files_necessary": ["t.py"],
                "questions": [
                    {
                        "name": "Q1",
                        "marking_items": [
                            {
                                "target_file": "t.py",
                                "total_mark": 1,
                                "type": "file_exists",
                            }
                        ],
                    }
                ],
            }
        )
    assert "language" in str(excinfo.value)


if __name__ == "__main__":
    test_language_validation()
    print("Language validation test passed!")
