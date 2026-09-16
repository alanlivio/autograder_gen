import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import yaml
import autograder_gen as ag

EXAMPLES = [
    {
        "example": "py_simple",
        "cases": [
            ("correct_answer", None),
            ("wrong_answer", 0),
            ("compiler_error", 0),
            ("missing_file", 0),
        ],
    },
    {
        "example": "py_function",
        "cases": [
            ("correct_answer", None),
            ("wrong_answer", 5),
            ("compiler_error", 0),
            ("missing_file", 0),
        ],
    },
    {
        "example": "py_complete",
        "cases": [
            ("correct_answer", None),
            ("wrong_answer", 67),
            ("compiler_error", 75),
            ("missing_file", 0),
        ],
    },
    {
        "example": "java_simple",
        "cases": [
            ("correct_answer", None),
            ("wrong_answer", 0),
            ("compiler_error", 0),
            ("missing_file", 0),
        ],
    },
]


def run_example_case(
    runner: ag.AutograderRunner,
    base_dir: Path,
    example_name: str,
    subdir: str,
    expected_score: int | None,
):
    example_dir = base_dir / "tests/examples" / example_name
    student_dir = example_dir / subdir

    if expected_score is None and runner.config_obj is not None:
        expected_score = runner.config_obj.total_score

    try:
        results = runner.run_autograder_for_submission(student_dir, expected_score=expected_score)
    except Exception as e:
        print(f"\n[FAIL] {e}")
        return "FAIL", None, expected_score

    tests = results.get("tests", [])
    total_score = sum(t.get("score", 0) for t in tests)
    matched = total_score == expected_score
    status_label = "PASS" if matched else "FAIL"

    return status_label, total_score, expected_score


def main():
    base_dir = Path(__file__).resolve().parent.parent
    filter_examples = sys.argv[1:]

    for group in EXAMPLES:
        ex = group["example"]
        if filter_examples and ex not in filter_examples:
            continue

        if ex == "java_simple" and shutil.which("javac") is None:
            for subdir, expected in group["cases"]:
                print(f"\n[SKIPPED] {ex}/{subdir}: javac is not installed")
            continue

        example_dir = base_dir / "tests/examples" / ex
        config_path = example_dir / "config.yaml"
        runner = ag.AutograderRunner(config_path)

        for subdir, expected in group["cases"]:
            run_example_case(runner, base_dir, ex, subdir, expected)

        if sys.stdin.isatty():
            try:
                input("\nPress Enter to continue...")
            except EOFError:
                pass
            except KeyboardInterrupt:
                print("\nAborted.")
                sys.exit(130)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)
