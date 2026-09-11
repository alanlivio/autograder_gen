import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
import yaml
import autograder_gen as ag


def run_autograder_sh_scenario(
    example_name: str,
    subdir: str,
    expected_score: int,
    config_file: str = "config.yaml",
):
    base_dir = Path(__file__).parent.parent.parent
    example_dir = base_dir / "tests/examples" / example_name
    config_path = example_dir / config_file
    student_dir = example_dir / subdir

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        config = ag.Config.parse(config_path)

        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix.lower() in [".yaml", ".yml"]:
                original_config = yaml.safe_load(f)
            else:
                original_config = json.load(f)

        generator = ag.Engine(config, original_config)
        gen_dir = tmp_path / "gen"
        output_zip = generator.generate(str(gen_dir))

        source_dir = tmp_path / "source"
        submission_dir = tmp_path / "submission"
        results_dir = tmp_path / "results"
        source_dir.mkdir()
        submission_dir.mkdir()

        with zipfile.ZipFile(output_zip, "r") as z:
            z.extractall(source_dir)

        if student_dir.exists():
            for f in student_dir.iterdir():
                if f.is_file():
                    shutil.copy(f, submission_dir / f.name)

        script_path = source_dir / "run_autograder.sh"
        if not script_path.exists():
            script_path = source_dir / "run_autograder"
        assert script_path.exists()
        os.chmod(script_path, 0o755)

        results_path = results_dir / "results.json"
        process = subprocess.run(
            ["bash", str(script_path)],
            cwd=source_dir,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "AUTOGRADER_ROOT": str(tmp_path),
                "PYTHON": sys.executable,
            },
        )

        assert results_path.exists(), f"results.json not created. stderr: {process.stderr}, stdout: {process.stdout}"

        with open(results_path, "r", encoding="utf-8") as f:
            results = json.load(f)

        assert "tests" in results
        total_score = sum(t.get("score", 0) for t in results["tests"])
        print(f"[{example_name}] ({subdir}): expected score={expected_score}, actual score={total_score}")
        assert total_score == expected_score


@pytest.mark.parametrize(
    "example_name, subdir, expected_score",
    [
        ("py_simple", "correct_answer", 10),
        ("py_simple", "wrong_answer", 0),
        ("py_simple", "compiler_error", 0),
        ("py_simple", "missing_file", 0),
        ("py_function", "correct_answer", 10),
        ("py_function", "wrong_answer", 5),
        ("py_function", "compiler_error", 0),
        ("py_function", "missing_file", 0),
        ("py_complete", "correct_answer", 100),
        ("py_complete", "wrong_answer", 67),
        ("py_complete", "compiler_error", 75),
        ("py_complete", "missing_file", 0),
        ("java_simple", "correct_answer", 10),
        ("java_simple", "wrong_answer", 0),
        ("java_simple", "compiler_error", 0),
        ("java_simple", "missing_file", 0),
    ],
)
def test_examples_run_autograder_sh(example_name, subdir, expected_score):
    if example_name == "java_simple" and shutil.which("javac") is None:
        pytest.skip("javac is not installed")
    run_autograder_sh_scenario(example_name, subdir, expected_score)
