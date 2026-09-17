import zipfile
import tempfile
import shutil
import pytest
import autograder_gen as ag
from autograder_gen.grader_utils import StudentMessage

CONFIG_FOR_TEMPLATES = {
    "version": "1.0",
    "language": "python",
    "setup_commands": ["pip install numpy pandas matplotlib"],
    "files_necessary": ["solution.py", "math_functions.py"],
    "questions": [
        {
            "name": "Question 1",
            "marking_items": [
                {
                    "target_file": "solution.py",
                    "total_mark": 10,
                    "type": "file_exists",
                    "name": "check_solution_py_exists",
                },
                {
                    "target_file": "solution.py",
                    "total_mark": 5,
                    "type": "output_comparison",
                    "name": "basic_addition_test",
                    "expected_output": "test",
                },
            ],
        }
    ],
}


@pytest.fixture
def temp_output_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d)


def test_setup_sh_contains_setup_commands(temp_output_dir):
    config = ag.Config.model_validate(CONFIG_FOR_TEMPLATES)
    generator = ag.Engine(config, CONFIG_FOR_TEMPLATES)
    zip_path = generator.generate(temp_output_dir)
    with zipfile.ZipFile(zip_path, "r") as z:
        with z.open("setup.sh") as f:
            content = f.read().decode()
            assert "pip install numpy pandas matplotlib" in content
            assert "Setup completed successfully" in content


def test_run_autograder_copies_files(temp_output_dir):
    config = ag.Config.model_validate(CONFIG_FOR_TEMPLATES)
    generator = ag.Engine(config, CONFIG_FOR_TEMPLATES)
    zip_path = generator.generate(temp_output_dir)
    with zipfile.ZipFile(zip_path, "r") as z:
        with z.open("run_autograder") as f:
            content = f.read().decode()
            assert "Copying required submission files to source directory" in content
            # Check for files in files_necessary
            for fname in CONFIG_FOR_TEMPLATES["files_necessary"]:
                assert fname in content


def test_per_question_test_file_content(temp_output_dir):
    config = ag.Config.model_validate(CONFIG_FOR_TEMPLATES)
    generator = ag.Engine(config, CONFIG_FOR_TEMPLATES)
    zip_path = generator.generate(temp_output_dir)
    with zipfile.ZipFile(zip_path, "r") as z:
        # The first question should now be question_1_test.py
        test_file = "tests/question_1_test.py"
        assert test_file in z.namelist()
        with z.open(test_file) as f:
            content = f.read().decode()
            # Check for the new test class name
            assert "class TestQuestion1" in content
            # Check for test methods generated from the sample config names
            assert "def test_check_solution_py_exists" in content
            assert "def test_basic_addition_test" in content


def test_java_setup_sh_contains_default_jdk(temp_output_dir):
    java_config = CONFIG_FOR_TEMPLATES.copy()
    java_config["language"] = "java"
    config = ag.Config.model_validate(java_config)
    generator = ag.Engine(config, java_config)
    zip_path = generator.generate(temp_output_dir)
    with zipfile.ZipFile(zip_path, "r") as z:
        with z.open("setup.sh") as f:
            content = f.read().decode()
            assert "apt-get install -y default-jdk" in content
            assert "Setup completed successfully" in content


def test_output_comparison_template(tmp_path):
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
                        "type": "output_comparison",
                        "name": "output_test",
                        "expected_output": "42",
                    },
                ],
            }
        ],
    }
    config = ag.Config.model_validate(config_dict)
    generator = ag.Engine(config, config_dict)
    output_dir = tmp_path / "output_oc"
    zip_path = generator.generate(str(output_dir))

    with zipfile.ZipFile(zip_path, "r") as z:
        assert "grader_utils.py" in z.namelist()
        test_content = z.read("tests/question_1_test.py").decode("utf-8")

        assert "def test_output_test(self):" in test_content
        assert 'print(f"# 1.1) output_test")' in test_content
        assert "from grader_utils import StudentMessage, normalize" in test_content
        assert "self.fail(StudentMessage.COMPILER_ERROR)" in test_content
        assert "self.fail(StudentMessage.RUNTIME_ERROR)" in test_content
        assert "StudentMessage.WRONG_ANSWER_FILE.format(file_name=target_file)" in test_content
        assert "StudentMessage.CORRECT_ANSWER_FILE.format(file_name=target_file)" in test_content
        assert "StudentMessage.TIME_LIMIT_EXCEEDED_FILE.format(seconds=" in test_content
        assert "expected_out = normalize(expected_output)" in test_content
        assert "actual_out = normalize(result.stdout)" in test_content


def test_function_test_template_expected_actual_output(tmp_path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "Math Test",
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
    output_dir = tmp_path / "output_fn"
    zip_path = generator.generate(str(output_dir))

    with zipfile.ZipFile(zip_path, "r") as z:
        assert "grader_utils.py" in z.namelist()
        test_content = z.read("tests/question_1_test.py").decode("utf-8")
        assert 'print(f"# 1.1) Math Test")' in test_content
        assert 'expected_out = normalize("3")' in test_content
        assert "actual_out = normalize(str(result))" in test_content
        assert "from grader_utils import StudentMessage, normalize" in test_content
        assert (
            "StudentMessage.WRONG_ANSWER_FUNCTION.format(function_name=function_name)"
            in test_content
        )
        assert (
            "StudentMessage.CORRECT_ANSWER_FUNCTION.format(function_name=function_name)"
            in test_content
        )
        assert "StudentMessage.TIME_LIMIT_EXCEEDED_FUNCTION.format(seconds=" in test_content
        assert (
            "StudentMessage.ERROR_FUNCTION_NOT_CALLABLE.format(function_name=function_name)"
            in test_content
        )


def test_file_exists_template_student_message(tmp_path):
    config_dict = {
        "version": "1.0",
        "language": "python",
        "files_necessary": ["solution.py"],
        "questions": [
            {
                "name": "File Existence",
                "marking_items": [
                    {
                        "target_file": "solution.py",
                        "total_mark": 10,
                        "type": "file_exists",
                    }
                ],
            }
        ],
    }
    config = ag.Config.model_validate(config_dict)
    generator = ag.Engine(config, config_dict)
    output_dir = tmp_path / "output_fe"
    zip_path = generator.generate(str(output_dir))

    with zipfile.ZipFile(zip_path, "r") as z:
        assert "grader_utils.py" in z.namelist()
        test_content = z.read("tests/question_1_test.py").decode("utf-8")
        assert "from grader_utils import StudentMessage, normalize" in test_content
        assert "StudentMessage.WRONG_FILE.format(file_name=target_file)" in test_content
        assert "StudentMessage.CORRECT_FILE.format(file_name=target_file)" in test_content
        assert "self.fail(StudentMessage.WRONG_FILE.format(file_name=target_file))" in test_content
