import subprocess
import sys
import tempfile
import shutil
import json
import os
import pytest

MAIN_PATH = "autograder_gen/cli.py"

INVALID_CONFIG = {
    # Missing 'questions' and 'files_necessary'
    "version": "1.0",
    "language": "python",
    "global_time_limit": 300,
}

UNSUPPORTED_LANG_CONFIG = {
    "version": "1.0",
    "language": "brainfuck",
    "global_time_limit": 300,
    "files_necessary": ["solution.bf"],
    "questions": [],
}


@pytest.fixture
def temp_config_file():
    temp_dir = tempfile.mkdtemp()

    def _write_config(data):
        path = os.path.join(temp_dir, "config.yaml")
        with open(path, "w") as f:
            json.dump(data, f)
        return path

    yield _write_config
    shutil.rmtree(temp_dir)


def test_cli_invalid_config(temp_config_file):
    config_path = temp_config_file(INVALID_CONFIG)
    result = subprocess.run(
        [sys.executable, MAIN_PATH, "--config", config_path],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "error" in result.stdout.lower() or "error" in result.stderr.lower()


def test_cli_unsupported_language(temp_config_file):
    config_path = temp_config_file(UNSUPPORTED_LANG_CONFIG)
    result = subprocess.run(
        [sys.executable, MAIN_PATH, "--config", config_path],
        capture_output=True,
        text=True,
    )
    # Depending on implementation, may pass validation but fail generation
    if result.returncode == 0:
        # Try to generate
        temp_dir = tempfile.mkdtemp()
        try:
            result2 = subprocess.run(
                [
                    sys.executable,
                    MAIN_PATH,
                    "--config",
                    config_path,
                    "--output",
                    temp_dir,
                ],
                capture_output=True,
                text=True,
            )
            assert result2.returncode != 0
            assert (
                "unsupported" in result2.stdout.lower()
                or "unsupported" in result2.stderr.lower()
                or "error" in result2.stdout.lower()
                or "error" in result2.stderr.lower()
            )
        finally:
            shutil.rmtree(temp_dir)
    else:
        assert (
            "unsupported" in result.stdout.lower()
            or "unsupported" in result.stderr.lower()
            or "error" in result.stdout.lower()
            or "error" in result.stderr.lower()
        )
