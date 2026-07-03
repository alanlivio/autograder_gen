import os
import zipfile
import tempfile
import shutil
import yaml
import pytest

from autograder_gen.generator import AutograderGenerator
from autograder_gen.config import ConfigParser

from autograder_gen.config import AutograderConfigModel

SAMPLE_CONFIG_DICT = {
    "version": "1.0",
    "language": "python",
    "files_necessary": ["solution.py"],
    "questions": [
        {
            "name": "Question 1",
            "marking_items": [
                {
                    "target_file": "solution.py",
                    "total_mark": 10,
                    "type": "file_exists",
                    "name": "check_solution_py_exists",
                }
            ],
        }
    ],
}


@pytest.fixture
def temp_output_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


def test_autograder_zip_contains_expected_files(temp_output_dir):
    # Use schema to parse the manual dict
    config = AutograderConfigModel.model_validate(SAMPLE_CONFIG_DICT)

    generator = AutograderGenerator(config, SAMPLE_CONFIG_DICT)
    zip_path = generator.generate(temp_output_dir)

    # Check that the zip file exists
    assert os.path.exists(zip_path)

    # Check contents of the zip
    with zipfile.ZipFile(zip_path, "r") as z:
        namelist = z.namelist()
        # Basic expected files
        expected_files = [
            "setup.sh",
            "run_autograder",
            "run_tests.py",
            "requirements.txt",
            "autograder_gen.yaml",
            "README.md",
            "tests/",
        ]
        for fname in expected_files:
            assert any(
                f.startswith(fname) for f in namelist
            ), f"Missing {fname} in zip: {namelist}"

        # Verify the original config was saved correctly
        with z.open("autograder_gen.yaml") as f:
            saved_config = yaml.safe_load(f.read().decode("utf-8"))
            assert (
                saved_config == SAMPLE_CONFIG_DICT
            ), "Original config not preserved correctly"

        # At least one test file per question (now by number)
        for idx, q in enumerate(SAMPLE_CONFIG_DICT["questions"], 1):
            test_file = f"tests/question_{idx}_test.py"
            assert test_file in namelist, f"Missing {test_file} in zip: {namelist}"
