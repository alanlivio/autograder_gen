"""
Command Line Interface for AutograderGen.
Provides CLI commands for validating configurations and generating Gradescope autograders.
"""

import argparse
import json
import sys
import zipfile
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import autograder_gen as ag
from autograder_gen.engine_utils import (
    print_error,
    print_success,
    print_warning,
    setup_logging,
)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate Gradescope autograder script from YAML configuration. "
            "Generated files will be at the same folder as the config "
            "(autograder.zip, stub submissions for testing, "
            "and optionally description.docx and description.md when --descriptions is specified)."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--config", "-c", help="Path to YAML configuration file")
    parser.add_argument(
        "--descriptions",
        "--description",
        action="store_true",
        default=False,
        help="Generate description.docx and description.md assessment descriptions",
    )
    parser.add_argument(
        "--run-submission",
        "-r",
        dest="run_submission",
        help="Path to submission directory or zip file to run using AutograderRunner",
    )
    parser.add_argument(
        "--run-stub-submissions",
        dest="run_stubs_submissions",
        nargs="?",
        const=True,
        default=False,
        help="Run autograder for generated stub submissions (stub_correct_answer.zip, stub_wrong_answer.zip, stub_compiler_error.zip, stub_correct_answer_wrong_location.zip)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="Print full autograder execution logs instead of only paths to log files",
    )
    args = parser.parse_args()
    setup_logging()
    try:
        config_arg = args.config
        if not config_arg:
            if isinstance(args.run_stubs_submissions, str):
                config_arg = args.run_stubs_submissions
            elif args.run_submission:
                sub_p = Path(args.run_submission)
                for candidate in (
                    sub_p / "config.yaml",
                    sub_p / "config.yml",
                    sub_p.parent / "config.yaml",
                    sub_p.parent / "config.yml",
                ):
                    if candidate.is_file():
                        config_arg = str(candidate)
                        break
            elif args.run_stubs_submissions:
                for candidate in (
                    Path("config.yaml"),
                    Path("config.yml"),
                    Path("output/autograder.zip"),
                    Path("autograder.zip"),
                ):
                    if candidate.is_file():
                        config_arg = str(candidate)
                        break
            if not config_arg:
                print_error("Error: --config / -c is required")
                return 2

        path = Path(config_arg)
        if not path.exists():
            print_error(f"Configuration file not found: {path}")
            return 1

        if path.is_file() and (path.suffix.lower() == ".zip" or zipfile.is_zipfile(path)):
            with zipfile.ZipFile(path, "r") as z:
                if "autograder_gen.yaml" in z.namelist():
                    raw_config_data = yaml.safe_load(z.read("autograder_gen.yaml"))
                else:
                    print_error(f"autograder_gen.yaml not found in zip archive: {path}")
                    return 1
        else:
            with open(path, "r", encoding="utf-8") as f:
                raw_config_data = yaml.safe_load(f)

        validator = ag.Validator()
        is_valid = validator.validate_json(raw_config_data)
        errors = validator.get_errors()
        warnings = validator.get_warnings()
        if not (args.run_submission or args.run_stubs_submissions):
            for warning in warnings:
                print_warning(warning)
        if not is_valid:
            print_error("Configuration validation failed:")
            for error in errors:
                print_error(f"  - {error}")
            return 1
        if not (args.run_submission or args.run_stubs_submissions):
            print_success("Configuration validation passed")

        output_dir = path.parent if str(path.parent) != "" else Path(".")
        if args.run_submission:
            sub_path = Path(args.run_submission)
            if not sub_path.exists():
                print_error(f"Submission path not found: {args.run_submission}")
                return 1
            runner = ag.AutograderRunner(path, verbose=args.verbose)
            res = runner.run_autograder_for_submission(
                sub_path, log_path=output_dir / "submission.log", verbose=args.verbose
            )
            if "log_path" in res:
                log_p = Path(res["log_path"])
                try:
                    display_path = str(log_p.resolve().relative_to(Path.cwd().resolve()))
                except ValueError:
                    display_path = str(log_p)
                print(display_path)
            return 0

        if args.run_stubs_submissions:
            runner = ag.AutograderRunner(path, verbose=args.verbose)
            runner.run_autograder_for_generated_submissions(verbose=args.verbose)
            return 0
        config = ag.Config.model_validate(raw_config_data)
        original_config_dict = None
        try:
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
        print(f"  Required Files: {', '.join(summary['required_files'])}")

        output_dir = path.parent if str(path.parent) != "" else Path(".")
        generator = ag.Engine(config, original_config_dict, base_dir=path.parent)
        output_path = generator.generate(str(output_dir), descriptions=args.descriptions)
        print_success(f"Autograder package generated successfully at: {output_dir}")
        assets_desc = "description.docx, description.md, " if args.descriptions else ""
        print_success(
            f"Generated assets: autograder.zip, {assets_desc}"
            "stub submissions for testing (stub_correct_answer.zip, stub_wrong_answer.zip, stub_compiler_error.zip, stub_correct_answer_wrong_location.zip)"
        )
        return 0
    except Exception as e:
        print_error(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
