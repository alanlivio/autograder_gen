import yaml
from pathlib import Path
from typing import Dict, List, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError


class MarkingItem(BaseModel):
    """Represents a single marking item within a question."""

    target_file: str = ""
    total_mark: float
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
            "gitlab_submission_exists",
            "github_submission_exists",
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
    def validate_type_fields(self) -> "MarkingItem":
        if (
            self.type not in ("output_comparison", "function_test")
            and "time_limit" in self.model_fields_set
        ):
            raise ValueError(f"time_limit is not allowed for type '{self.type}'")
        if self.type == "function_test" and not self.function_name:
            raise ValueError("function_name is required for function_test")
        if (
            self.type not in ("gitlab_submission_exists", "github_submission_exists")
            and not self.target_file
        ):
            raise ValueError(f"target_file is required for type '{self.type}'")
        return self


class Question(BaseModel):
    """Represents a question with multiple marking items."""

    name: str
    description: str = ""
    strict_float: bool = False
    marking_items: List[MarkingItem] = Field(min_length=1)


class Config(BaseModel):
    """Complete autograder configuration."""

    version: str
    language: str
    global_time_limit: int = 300
    strict_file_location: bool = False
    remove_use_of_java_package: bool = False
    retrieve_student_id: bool = False
    wrong_file_location_deduction: float = 0.0
    setup_commands: List[str] = Field(default_factory=list)
    required_files: List[str] = Field(default_factory=list)
    questions: List[Question] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def handle_required_files_backwards_compat(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "required_files" not in data or not data["required_files"]:
                if "src_files" in data and data["src_files"]:
                    data["required_files"] = data["src_files"]
                elif "files_necessary" in data and data["files_necessary"]:
                    data["required_files"] = data["files_necessary"]
            if "src_files" not in data and "required_files" in data:
                data["src_files"] = data["required_files"]
            if "files_necessary" not in data and "required_files" in data:
                data["files_necessary"] = data["required_files"]
        return data

    @property
    def files_necessary(self) -> List[str]:
        return self.required_files

    @property
    def src_files(self) -> List[str]:
        return self.required_files

    @field_validator("language")
    @classmethod
    def check_language(cls, v: str) -> str:
        allowed = {"python", "java"}
        if v not in allowed:
            raise ValueError(f"language must be one of: {allowed}")
        return v

    @model_validator(mode="after")
    def validate_target_files(self) -> "Config":
        for i, q in enumerate(self.questions):
            for j, item in enumerate(q.marking_items):
                target = item.target_file
                if target and target not in self.required_files:
                    raise ValueError(
                        f"Question '{q.name}', Item {j+1}: Target file '{target}' is not listed in 'required_files'"
                    )
        return self

    @model_validator(mode="after")
    def validate_wrong_file_location_deduction(self) -> "Config":
        if self.wrong_file_location_deduction < 0:
            raise ValueError("wrong_file_location_deduction must be non-negative")
        if self.strict_file_location and self.wrong_file_location_deduction > 0:
            raise ValueError(
                "wrong_file_location_deduction is only supported when strict_file_location is False"
            )
        return self

    @property
    def total_score(self) -> float:
        return sum(item.total_mark for q in self.questions for item in q.marking_items)

    def get_config_summary(self) -> Dict[str, Any]:
        total_items = 0
        total_marks = 0.0
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
            "retrieve_student_id": self.retrieve_student_id,
            "wrong_file_location_deduction": self.wrong_file_location_deduction,
            "required_files": self.required_files,
            "src_files": self.required_files,
            "files_necessary": self.required_files,
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

        # 1. Search inside autograder_gen/examples package directory
        pkg_example_path = Path(__file__).parent / "examples" / example_key / "config.yaml"
        if pkg_example_path.exists():
            with open(pkg_example_path, "r", encoding="utf-8") as f:
                return f.read()

        # 2. Search inside repository tests/examples directory (fallback)
        repo_example_path = Path(__file__).parent.parent / "tests" / "examples" / example_key / "config.yaml"
        if repo_example_path.exists():
            with open(repo_example_path, "r", encoding="utf-8") as f:
                return f.read()

        raise FileNotFoundError(f"Example configuration file not found for example '{name}'")

    @staticmethod
    def parse(config_path: Any) -> "Config":
        """Parse the configuration file (YAML only)."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        if path.suffix.lower() not in [".yaml", ".yml"]:
            raise ValueError("Only YAML format (.yml, .yaml) is supported.")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            return Config.model_validate(data)

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid format in YAML configuration file: {e}")
        except ValidationError as e:
            raise e
        except Exception as e:
            raise ValueError(f"Error parsing configuration: {e}")

    @classmethod
    def normalize(cls, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize configuration data dictionary."""
        model = cls.model_validate(config_data)
        dump = model.model_dump()
        dump["setup_commands"] = [
            cmd.strip() for cmd in dump.get("setup_commands", []) if cmd and cmd.strip()
        ]
        dump["required_files"] = [
            f.strip() for f in dump.get("required_files", []) if f and f.strip()
        ]
        dump["src_files"] = dump["required_files"]
        dump["files_necessary"] = dump["required_files"]
        return dump


def normalize_autograder_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    return Config.normalize(config_data)


if __name__ == "__main__":
    import json

    print(json.dumps(MarkingItem.model_json_schema(), indent=2))
