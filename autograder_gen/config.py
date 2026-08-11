import yaml
from pathlib import Path
from typing import Dict, List, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError


class MarkingItemModel(BaseModel):
    """Represents a single marking item within a question."""

    target_file: str
    total_mark: int
    type: str
    time_limit: int = 30
    visibility: str = "visible"
    name: str = ""
    expected_input: str = ""
    expected_output: str = ""

    # Function testing fields
    function_name: str = ""
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)

    # Signature checking fields
    expected_parameters: str = ""
    expected_return_type: str = ""

    @field_validator("type")
    @classmethod
    def check_type(cls, v: str) -> str:
        allowed = {
            "file_exists",
            "output_comparison",
            "signature_check",
            "function_test",
        }
        if v not in allowed:
            raise ValueError(f"type must be one of: {allowed}")
        return v

    @field_validator("visibility")
    @classmethod
    def check_visibility(cls, v: str) -> str:
        allowed = {"visible", "hidden", "after_due_date", "after_published"}
        if v not in allowed:
            raise ValueError(f"visibility must be one of: {allowed}")
        return v

    @model_validator(mode="after")
    def validate_type_fields(self) -> "MarkingItemModel":
        if self.type == "function_test" and not self.function_name:
            raise ValueError("function_name is required for function_test")
        return self


class QuestionModel(BaseModel):
    """Represents a question with multiple marking items."""

    name: str
    description: str = ""
    marking_items: List[MarkingItemModel] = Field(min_length=1)


class AutograderConfigModel(BaseModel):
    """Complete autograder configuration."""

    version: str
    language: str
    global_time_limit: int = 300
    setup_commands: List[str] = Field(default_factory=list)
    files_necessary: List[str] = Field(default_factory=list)
    questions: List[QuestionModel] = Field(min_length=1)

    @field_validator("language")
    @classmethod
    def check_language(cls, v: str) -> str:
        allowed = {"python", "java"}
        if v not in allowed:
            raise ValueError(f"language must be one of: {allowed}")
        return v

    @model_validator(mode="after")
    def validate_target_files(self) -> "AutograderConfigModel":
        for i, q in enumerate(self.questions):
            for j, item in enumerate(q.marking_items):
                target = item.target_file
                if target and target not in self.files_necessary:
                    raise ValueError(
                        f"Question '{q.name}', Item {j+1}: Target file '{target}' is not listed in 'files_necessary'"
                    )
        return self

    def get_config_summary(self) -> Dict[str, Any]:
        total_items = 0
        total_marks = 0
        visibility_counts: Dict[str, int] = {}
        for q in self.questions:
            for item in q.marking_items:
                total_items += 1
                total_marks += item.total_mark
                vis = item.visibility
                visibility_counts[vis] = visibility_counts.get(vis, 0) + 1

        return {
            "version": self.version,
            "language": self.language,
            "global_time_limit": self.global_time_limit,
            "total_questions": len(self.questions),
            "total_marking_items": total_items,
            "total_marks": total_marks,
            "files_necessary": self.files_necessary,
            "visibility_counts": visibility_counts,
        }

    @staticmethod
    def get_example_config_yaml(name: str = "py_simple") -> str:
        """Return example YAML configuration content by example name."""
        key_map = {
            "py_simple": "py_simple",
            "py_function": "py_function",
            "py_complete": "py_complete",
            "java_simple": "java_simple",
        }
        example_key = key_map.get(name.lower(), "py_simple")

        pkg_dir = Path(__file__).parent.parent
        example_path = pkg_dir / "tests" / "examples" / example_key / "config.yaml"
        if example_path.exists():
            with open(example_path, "r", encoding="utf-8") as f:
                return f.read()

        raise FileNotFoundError(f"Example configuration file not found: {example_path}")


AutograderConfig = AutograderConfigModel
Question = QuestionModel
MarkingItem = MarkingItemModel


class ConfigParser:
    """Parses YAML configuration files for autograder generation."""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

    def parse(self) -> AutograderConfig:
        """Parse the configuration file (YAML only)."""
        if self.config_path.suffix.lower() not in [".yaml", ".yml"]:
            raise ValueError("Only YAML format (.yml, .yaml) is supported.")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            return AutograderConfig.model_validate(data)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid format in YAML configuration file: {e}")
        except ValidationError as e:
            # We let ValidationError bubble up
            raise e
        except Exception as e:
            raise ValueError(f"Error parsing configuration: {e}")

    def parse_and_validate(self) -> AutograderConfig:
        """Parse and validate the configuration file."""
        return self.parse()


def normalize_autograder_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    model = AutograderConfigModel.model_validate(config_data)
    dump = model.model_dump()
    dump["setup_commands"] = [
        cmd.strip() for cmd in dump.get("setup_commands", []) if cmd and cmd.strip()
    ]
    dump["files_necessary"] = [
        f.strip() for f in dump.get("files_necessary", []) if f and f.strip()
    ]
    return dump


if __name__ == "__main__":
    import json

    print(json.dumps(MarkingItemModel.model_json_schema(), indent=2))
