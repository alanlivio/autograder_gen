import sys
from pathlib import Path
import pytest

from autograder_gen.batch_gen import find_configs as find_configs_gen, main as batch_gen_main
from autograder_gen.batch_run import find_configs as find_configs_run, main as batch_run_main


def test_find_configs_single_file(tmp_path: Path):
    cfg = tmp_path / "config.yml"
    cfg.write_text("version: '1.0'", encoding="utf-8")
    assert find_configs_gen(cfg) == [cfg]
    assert find_configs_run(cfg) == [cfg]


def test_find_configs_directory_direct(tmp_path: Path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text("version: '1.0'", encoding="utf-8")
    assert find_configs_gen(tmp_path) == [cfg]
    assert find_configs_run(tmp_path) == [cfg]


def test_find_configs_directory_nested(tmp_path: Path):
    sub1 = tmp_path / "sub1"
    sub1.mkdir()
    cfg1 = sub1 / "config.yml"
    cfg1.write_text("version: '1.0'", encoding="utf-8")

    sub2 = tmp_path / "sub2"
    sub2.mkdir()
    cfg2 = sub2 / "config.yaml"
    cfg2.write_text("version: '1.0'", encoding="utf-8")

    configs = find_configs_gen(tmp_path)
    assert len(configs) == 2
    assert cfg1 in configs
    assert cfg2 in configs


def test_batch_gen_main_no_args(capsys):
    sys.argv = ["autograder-gen-batch"]
    with pytest.raises(SystemExit) as exc_info:
        batch_gen_main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Usage:" in captured.err


def test_batch_run_main_no_args(capsys):
    sys.argv = ["autograder-run-batch"]
    with pytest.raises(SystemExit) as exc_info:
        batch_run_main()
    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Usage:" in captured.err


def test_batch_gen_execution(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = """version: '1.0'
language: python
required_files:
  - test.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: output_comparison
        target_file: test.py
"""
    cfg_path.write_text(cfg_content, encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["autograder-gen-batch", str(tmp_path)])
    batch_gen_main()

    captured = capsys.readouterr()
    for asset_name in [
        "autograder.zip",
        "stub_correct_answer.zip",
        "stub_wrong_answer.zip",
        "stub_compiler_error.zip",
        "stub_correct_answer_wrong_location.zip",
    ]:
        assert asset_name in captured.out
        assert (tmp_path / asset_name).exists()
    assert not (tmp_path / "description.docx").exists()
    assert not (tmp_path / "description.md").exists()


def test_batch_gen_with_descriptions(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = """version: '1.0'
language: python
required_files:
  - test.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: output_comparison
        target_file: test.py
"""
    cfg_path.write_text(cfg_content, encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["autograder-gen-batch", "--descriptions", str(tmp_path)])
    batch_gen_main()

    captured = capsys.readouterr()
    for asset_name in [
        "autograder.zip",
        "stub_correct_answer.zip",
        "stub_wrong_answer.zip",
        "stub_compiler_error.zip",
        "stub_correct_answer_wrong_location.zip",
        "description.docx",
        "description.md",
    ]:
        assert asset_name in captured.out
        assert (tmp_path / asset_name).exists()


def test_batch_run_execution(tmp_path: Path, monkeypatch, capsys):
    cfg_path = tmp_path / "config.yaml"
    cfg_content = """version: '1.0'
language: python
required_files:
  - solution.py
questions:
  - name: Q1
    marking_items:
      - name: Item 1
        total_mark: 10
        type: function_test
        target_file: solution.py
        function_name: add
        test_cases:
          - args: [1, 2]
            expected: "3"
"""
    cfg_path.write_text(cfg_content, encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["autograder-run-batch", str(tmp_path)])
    batch_run_main()

    captured = capsys.readouterr()
    for log_name in [
        "stub_correct_answer.log",
        "stub_wrong_answer.log",
        "stub_compiler_error.log",
        "stub_correct_answer_wrong_location.log",
    ]:
        assert log_name in captured.out
        assert (tmp_path / log_name).exists()
