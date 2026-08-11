import os
import subprocess
import json
import yaml
import shutil
import tempfile
import pytest
from pathlib import Path
from autograder_gen.generator import AutograderGenerator
from autograder_gen.config import ConfigParser


def run_autograder_scenario(
    example_name: str,
    subdir: str = "correct_answer",
    expected_score: int = None,
    config_file: str = "config.yaml",
):
    """
    Reusable helper to run an autograder integration scenario.
    :param example_name: Name of the example folder (e.g., 'py_simple')
    :param subdir: Subfolder containing student code (e.g., 'correct_answer')
    :param expected_score: If provided, verify the total score matches this value.
    :param config_file: The configuration file to use (e.g., 'config.yaml' or 'config.yaml')
    """
    base_dir = Path(__file__).parent.parent.parent
    example_dir = base_dir / "tests/examples" / example_name
    config_path = example_dir / config_file
    student_dir = example_dir / subdir

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_dir = Path(tmp_dir)

        # 1. Generate autograder
        parser = ConfigParser(str(config_path))
        config = parser.parse()

        # Original config for generator (dict)
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix.lower() in [".yaml", ".yml"]:
                original_config = yaml.safe_load(f)
            else:
                original_config = json.load(f)

        generator = AutograderGenerator(config, original_config)
        gen_dir = tmp_dir / "generated"
        output_zip = generator.generate(str(gen_dir))

        # 2. Extract and Prepare Submission
        work_dir = tmp_dir / "run"
        work_dir.mkdir()

        import zipfile

        with zipfile.ZipFile(output_zip, "r") as z:
            z.extractall(work_dir)

        # Copy student files to submission
        submission_dir = work_dir / "submission"
        submission_dir.mkdir()

        # Copy ALL files from the student directory to handle multi-file scenarios
        if student_dir.exists():
            for student_file in student_dir.iterdir():
                if student_file.is_file():
                    shutil.copy(student_file, submission_dir / student_file.name)

        # 3. Run Autograder
        results_path = work_dir / "results.json"

        process = subprocess.run(
            [os.sys.executable, str(work_dir / "run_tests.py")],
            cwd=work_dir,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "PYTHONPATH": str(work_dir),
                "GRADESCOPE_RESULTS_PATH": str(results_path),
                "GRADESCOPE_SOURCE_PATH": str(submission_dir),
            },
        )

        # Assertions
        assert (
            results_path.exists()
        ), f"results.json not created for {example_name}/{subdir} with {config_file}. Error: {process.stderr}"

        with open(results_path, "r") as f:
            results = json.load(f)

        assert "tests" in results
        if expected_score is not None:
            total_score = sum(t.get("score", 0) for t in results["tests"])
            assert (
                total_score == expected_score
            ), f"Score mismatch for {example_name} ({config_file}). Expected {expected_score}, got {total_score}. Results: {results}"


@pytest.mark.parametrize(
    "subdir, expected_score",
    [
        ("correct_answer", 10),
        ("wrong_answer", 0),
        ("compiler_error", 0),
        ("missing_file", 0),
    ],
)
@pytest.mark.parametrize("config_file", ["config.yaml"])
def test_autograder_integration_py_simple(subdir, expected_score, config_file):
    """Test autograder execution for py_simple example across all scenarios."""
    run_autograder_scenario(
        "py_simple", subdir, expected_score, config_file=config_file
    )


@pytest.mark.parametrize(
    "subdir, expected_score",
    [
        ("correct_answer", 10),
        ("wrong_answer", 5),  # Signature check passes, function test fails
        ("compiler_error", 0),
        ("missing_file", 0),
    ],
)
@pytest.mark.parametrize("config_file", ["config.yaml"])
def test_autograder_integration_py_function(subdir, expected_score, config_file):
    """Test autograder execution for py_function example across all scenarios."""
    run_autograder_scenario(
        "py_function", subdir, expected_score, config_file=config_file
    )


@pytest.mark.parametrize(
    "subdir, expected_score",
    [
        ("correct_answer", 100),
        ("wrong_answer", 67),
        ("compiler_error", 75),  # Only some files have errors, others still pass tests
        ("missing_file", 0),
    ],
)
@pytest.mark.parametrize("config_file", ["config.yaml"])
def test_autograder_integration_py_complete(subdir, expected_score, config_file):
    """Test autograder execution for py_complete example across all scenarios."""
    run_autograder_scenario(
        "py_complete", subdir, expected_score, config_file=config_file
    )


