import os
import shutil
import tempfile
import zipfile
import yaml
import pytest

import autograder_gen as ag

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
                    "type": "output_comparison",
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
    config = ag.Config.model_validate(SAMPLE_CONFIG_DICT)

    generator = ag.Engine(config, SAMPLE_CONFIG_DICT)
    zip_path = generator.generate(temp_output_dir)

    assert os.path.exists(zip_path)

    with zipfile.ZipFile(zip_path, "r") as z:
        namelist = z.namelist()
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
            assert any(f.startswith(fname) for f in namelist), f"Missing {fname} in zip: {namelist}"

        with z.open("autograder_gen.yaml") as f:
            saved_config = yaml.safe_load(f.read().decode("utf-8"))
            assert saved_config == SAMPLE_CONFIG_DICT, "Original config not preserved correctly"

        for idx, q in enumerate(SAMPLE_CONFIG_DICT["questions"], 1):
            test_file = f"tests/question_{idx}_test.py"
            assert test_file in namelist, f"Missing {test_file} in zip: {namelist}"


def test_skeleton_generation():
    config_dict = {
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
                        "type": "function_test",
                        "function_name": "add",
                        "test_cases": [
                            {"args": [1, 2], "expected": "3"},
                            {"args": [5, 5], "expected": "10"},
                        ],
                    }
                ],
            }
        ],
    }
    config = ag.Config.model_validate(config_dict)
    generator = ag.Engine(config, config_dict)
    zip_bytes = generator.generate_correct_answer_zip()
    with zipfile.ZipFile(zip_bytes, "r") as z:
        assert "solution.py" in z.namelist()
        content = z.read("solution.py").decode("utf-8")
        assert "def add(*args, **kwargs):" in content
        assert "args == (1, 2)" in content
        assert "return 3" in content
        assert "args == (5, 5)" in content
        assert "return 10" in content


def test_skeleton_generation_java():
    config_dict = {
        "version": "1.0",
        "language": "java",
        "files_necessary": ["Solution.java"],
        "questions": [
            {
                "name": "Question 1",
                "marking_items": [
                    {
                        "target_file": "Solution.java",
                        "total_mark": 10,
                        "type": "function_test",
                        "function_name": "add",
                        "test_cases": [
                            {"args": [1, 2], "expected": "3"},
                            {"args": [5, 5], "expected": "10"},
                        ],
                    }
                ],
            }
        ],
    }
    config = ag.Config.model_validate(config_dict)
    generator = ag.Engine(config, config_dict)
    zip_bytes = generator.generate_correct_answer_zip()
    with zipfile.ZipFile(zip_bytes, "r") as z:
        assert "Solution.java" in z.namelist()
        content = z.read("Solution.java").decode("utf-8")
        assert "public class Solution {" in content
        assert "public static double add(double a, double b) {" in content
        assert "return a + b;" in content


def test_generator_essential_exports():
    config = ag.Config.model_validate(SAMPLE_CONFIG_DICT)
    generator = ag.Engine(config)

    docx_buf = generator.generate_description_docx()
    assert len(docx_buf.getvalue()) > 0

    md_buf = generator.generate_description_md()
    assert b"Assessment Description" in md_buf.getvalue()

    csv_buf = generator.generate_rubric_csv()
    assert b"Question,Marking Item,Type,Target File" in csv_buf.getvalue()

    correct_buf = generator.generate_correct_answer_zip()
    with zipfile.ZipFile(correct_buf, "r") as zf:
        assert len(zf.namelist()) > 0

    wrong_buf = generator.generate_wrong_answer_zip()
    with zipfile.ZipFile(wrong_buf, "r") as zf:
        assert len(zf.namelist()) > 0

    compiler_buf = generator.generate_compiler_error_zip()
    with zipfile.ZipFile(compiler_buf, "r") as zf:
        assert len(zf.namelist()) > 0

    wrong_loc_buf = generator.generate_correct_answer_wrong_location_zip()
    with zipfile.ZipFile(wrong_loc_buf, "r") as zf:
        assert len(zf.namelist()) > 0


def test_skeleton_generation_compiler_error():
    config_dict = {
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
                        "type": "function_test",
                        "function_name": "add",
                        "test_cases": [
                            {"args": [1, 2], "expected": "3"},
                        ],
                    }
                ],
            }
        ],
    }
    config = ag.Config.model_validate(config_dict)
    generator = ag.Engine(config, config_dict)
    zip_bytes = generator.generate_compiler_error_zip()
    with zipfile.ZipFile(zip_bytes, "r") as z:
        assert "solution.py" in z.namelist()
        content = z.read("solution.py").decode("utf-8")
        assert "def add(*args, **kwargs)" in content
