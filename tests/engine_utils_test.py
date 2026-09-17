import logging
from pathlib import Path
import pytest

from autograder_gen.engine_utils import (
    create_directory,
    format_error_message,
    get_file_extension,
    is_supported_language_file,
    print_error,
    print_info,
    print_success,
    print_warning,
    sanitize_filename,
    setup_logging,
    validate_directory_path,
    validate_file_path,
)


def test_setup_logging():
    setup_logging(verbose=True)
    assert logging.getLogger().level == logging.DEBUG
    setup_logging(verbose=False)
    assert logging.getLogger().level == logging.INFO


def test_validate_file_path(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("content")

    validated = validate_file_path(str(f))
    assert validated == f

    with pytest.raises(FileNotFoundError):
        validate_file_path(str(tmp_path / "non_existent.txt"))

    with pytest.raises(ValueError):
        validate_file_path(str(tmp_path))


def test_validate_directory_path(tmp_path):
    validated = validate_directory_path(str(tmp_path))
    assert validated == tmp_path

    with pytest.raises(FileNotFoundError):
        validate_directory_path(str(tmp_path / "non_existent_dir"))

    f = tmp_path / "file.txt"
    f.write_text("hello")
    with pytest.raises(ValueError):
        validate_directory_path(str(f))


def test_create_directory(tmp_path):
    target = tmp_path / "new_dir" / "sub_dir"
    created = create_directory(str(target))
    assert created == target
    assert target.is_dir()


def test_get_file_extension():
    assert get_file_extension("foo.py") == ".py"
    assert get_file_extension("foo.BAR.JAVA") == ".java"
    assert get_file_extension("foo") == ""


def test_is_supported_language_file():
    assert is_supported_language_file("main.py", "python")
    assert is_supported_language_file("Main.java", "java")
    assert not is_supported_language_file("main.cpp", "python")
    assert not is_supported_language_file("main.py", "unknown")


def test_sanitize_filename():
    assert sanitize_filename('test:file*name?.txt') == "test_file_name_.txt"
    assert sanitize_filename("   ...clean...   ") == "clean"
    assert sanitize_filename("   ...   ") == "unnamed"


def test_format_error_message():
    err = ValueError("Something broke")
    assert format_error_message(err) == "Something broke"
    assert format_error_message(err, "Context") == "Context: Something broke"


def test_print_helpers(capsys):
    print_success("worked")
    out, err = capsys.readouterr()
    assert "[OK] worked" in out

    print_error("failed")
    out, err = capsys.readouterr()
    assert "[ERROR] failed" in err

    print_warning("be careful")
    out, err = capsys.readouterr()
    assert "[WARNING] be careful" in out

    print_info("note")
    out, err = capsys.readouterr()
    assert "[INFO] note" in out
