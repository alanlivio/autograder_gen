"""
Command Line Interface for AutograderGen.
Provides CLI commands for validating configurations and generating Gradescope autograders.
"""

import argparse
import json
import sys
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from autograder_gen.config import (
    AutograderConfig,
    ConfigParser,
)
from autograder_gen.generator import AutograderGenerator
from autograder_gen.utils import (
    print_error,
    print_success,
    print_warning,
    setup_logging,
)
from autograder_gen.validator import ConfigValidator


def main():
    parser = argparse.ArgumentParser(
        description="Generate Gradescope autograder scripts from YAML configuration"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", "-c", help="Path to YAML configuration file")
    group.add_argument(
        "--example",
        "-e",
        help="Generate an example autograder YAML configuration file (py_simple, py_function, py_complete, java_simple)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="./output",
        help="Output directory for generated assessment files (autograder.zip, description.docx, description.md, rubric.csv, answers.zip)",
    )
    args = parser.parse_args()
    setup_logging()
    try:
        if args.example:
            out_dir = Path(args.output)
            out_dir.mkdir(parents=True, exist_ok=True)
            target_path = out_dir / f"{args.example}.yaml"
            yaml_str = AutograderConfig.get_example_config_yaml(args.example)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(yaml_str)
            print_success(
                f"Example '{args.example}' configuration generated at: {target_path}"
            )
            return 0
        with open(args.config, "r", encoding="utf-8") as f:
            raw_config_data = yaml.safe_load(f)
        # Validate configuration
        validator = ConfigValidator()
        is_valid = validator.validate_json(raw_config_data)
        errors = validator.get_errors()
        warnings = validator.get_warnings()
        for warning in warnings:
            print_warning(warning)
        if not is_valid:
            print_error("Configuration validation failed:")
            for error in errors:
                print_error(f"  - {error}")
            return 1
        print_success("Configuration validation passed")
        config = AutograderConfig.model_validate(raw_config_data)
        original_config_dict = None
        try:
            path = Path(args.config)
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix.lower() not in [".yaml", ".yml"]:
                    raise ValueError("File must be a YAML file (.yml or .yaml)")
                original_config_dict = yaml.safe_load(f)
        except Exception:
            pass  # If we can't load original config, proceed without it
        # Print assessment summary before generation process
        summary = config.get_config_summary()
        print_success(f"Assessment Summary (Config: {args.config}):")
        print(f"  Language: {summary['language']}")
        print(f"  Global Time Limit: {summary['global_time_limit']}s")
        print(f"  Total Questions: {summary['total_questions']}")
        print(f"  Total Marking Items: {summary['total_marking_items']}")
        print(f"  Total Marks: {summary['total_marks']}")
        print(f"  Necessary Files: {', '.join(summary['files_necessary'])}")

        generator = AutograderGenerator(config, original_config_dict)
        output_path = generator.generate(args.output)
        print_success(f"Autograder package generated successfully at: {args.output}")
        print_success(
            f"Generated assets: autograder.zip, description.docx, description.md, rubric.csv, correct_answer.zip, wrong_answer.zip"
        )
        return 0
    except Exception as e:
        print_error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
