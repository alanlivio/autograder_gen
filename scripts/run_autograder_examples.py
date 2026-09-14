import json
import os
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

SCENARIOS = [
    {
        "example": "py_simple",
        "cases": [
            ("correct_answer", 10),
            ("wrong_answer", 0),
            ("compiler_error", 0),
            ("missing_file", 0),
        ],
    },
    {
        "example": "py_function",
        "cases": [
            ("correct_answer", 10),
            ("wrong_answer", 5),
            ("compiler_error", 0),
            ("missing_file", 0),
        ],
    },
    {
        "example": "py_complete",
        "cases": [
            ("correct_answer", 100),
            ("wrong_answer", 67),
            ("compiler_error", 75),
            ("missing_file", 0),
        ],
    },
    {
        "example": "java_simple",
        "cases": [
            ("correct_answer", 10),
            ("wrong_answer", 0),
            ("compiler_error", 0),
            ("missing_file", 0),
        ],
    },
]


def run_scenario(
    runner: ag.AutograderRunner,
    base_dir: Path,
    example_name: str,
    subdir: str,
    expected_score: int,
):
    example_dir = base_dir / "tests/examples" / example_name
    student_dir = example_dir / subdir

    try:
        results = runner.run_autograder_for_submission(student_dir)
    except Exception as e:
        print(f"\n[FAIL] {e}")
        return "FAIL", None, expected_score

    tests = results.get("tests", [])
    total_score = sum(t.get("score", 0) for t in tests)
    max_possible = sum(t.get("max_score", 0) for t in tests)

    print("\n[STUDENT VIEW: Test Results]")
    for t in tests:
        number = t.get("number", "")
        num_str = f"[{number}] " if number else ""
        name = t.get("name", "Unknown test")
        score = t.get("score", 0)
        max_score = t.get("max_score", 0)
        status = t.get("status", "unknown").upper()
        output = t.get("output", "").strip()

        print(f"\n* {num_str}{name}")
        print(f"  Score: {score} / {max_score} pts | Status: {status}")
        if output:
            print("  Output:")
            for o_line in output.splitlines():
                print(f"    {o_line}")
        else:
            print("  Output: (no output)")

    matched = total_score == expected_score
    status_label = "PASS" if matched else "FAIL"

    print(f"\nTOTAL SCORE: {total_score} / {max_possible} pts (Expected: {expected_score}) -> [{status_label}]")

    return status_label, total_score, expected_score


def main():
    base_dir = Path(__file__).resolve().parent.parent
    filter_examples = sys.argv[1:]

    total = 0
    passed = 0
    skipped = 0
    failed = 0
    summary_rows = []

    for group in SCENARIOS:
        ex = group["example"]
        if filter_examples and ex not in filter_examples:
            continue

        if ex == "java_simple" and shutil.which("javac") is None:
            for subdir, expected in group["cases"]:
                total += 1
                print(f"\n{'#' * 80}")
                print(f"# SCENARIO: {ex} / {subdir} (Expected Score: {expected})")
                print(f"{'#' * 80}")
                print(f"\n[SKIPPED] {ex}/{subdir}: javac is not installed")
                summary_rows.append((ex, subdir, expected, None, "SKIPPED"))
                skipped += 1
            continue

        example_dir = base_dir / "tests/examples" / ex
        config_path = example_dir / "config.yaml"
        runner = ag.AutograderRunner(config_path)

        for subdir, expected in group["cases"]:
            total += 1
            print(f"\n{'#' * 80}")
            print(f"# SCENARIO: {ex} / {subdir} (Expected Score: {expected})")
            print(f"{'#' * 80}")
            status, actual, exp = run_scenario(runner, base_dir, ex, subdir, expected)
            summary_rows.append((ex, subdir, exp, actual, status))
            if status == "PASS":
                passed += 1
            elif status == "SKIPPED":
                skipped += 1
            else:
                failed += 1

            if sys.stdin.isatty():
                try:
                    input("\nPress Enter to continue...")
                except (EOFError, KeyboardInterrupt):
                    print()

    print("\nTEST EXAMPLES SUMMARY")
    print(f"{'Example':<16} {'Scenario':<18} {'Expected':<10} {'Actual':<10} {'Status':<8}")
    print("-" * 64)
    for ex, subdir, exp, actual, status in summary_rows:
        act_str = str(actual) if actual is not None else "N/A"
        print(f"{ex:<16} {subdir:<18} {exp:<10} {act_str:<10} {status:<8}")
    print("-" * 64)
    print(f"Total: {total} | Passed: {passed} | Skipped: {skipped} | Failed: {failed}\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
