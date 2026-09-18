from pathlib import Path
import re
from typing import Union


import math


def normalize_output(s: str) -> str:
    if s is None:
        return ""
    s = s.replace("\r\n", "\n")
    lines = [line.rstrip() for line in s.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def compare_outputs(
    actual: str,
    expected: str,
    strict_float: bool = False,
    rel_tol: float = 1e-4,
    abs_tol: float = 1e-4,
) -> bool:
    if actual == expected:
        return True
    if strict_float:
        return False
    try:
        a_val = float(actual.strip())
        e_val = float(expected.strip())
        return math.isclose(a_val, e_val, rel_tol=rel_tol, abs_tol=abs_tol)
    except (ValueError, TypeError):
        pass
    return False


def remove_package_line(path: Union[str, Path]) -> None:
    try:
        p = Path(path)
        if not p.exists() or not p.is_file():
            return
        content = p.read_text(encoding="utf-8", errors="replace")
        new_content = re.sub(
            r"^\s*package\s+[\w.]+\s*;[^\S\r\n]*(//.*)?(\r?\n)?",
            "",
            content,
            flags=re.MULTILINE,
        )
        if new_content != content:
            print(f"[INFO] removing not expected package line from {p.name}.")
            p.write_text(new_content, encoding="utf-8")
    except Exception:
        pass



class StudentMessageStr(str):
    def format(self, *args, **kwargs):
        if "target_file" in kwargs and "file_name" not in kwargs:
            kwargs["file_name"] = kwargs["target_file"]
        if "file_name" in kwargs and "target_file" not in kwargs:
            kwargs["target_file"] = kwargs["file_name"]
        return super().format(*args, **kwargs)


class StudentMessage:
    COMPILING = "## Compiling"
    RUNNING = "## Running"
    COMPARING_OUTPUT = "## Comparing output"
    INPUT = "### Input:"
    EXPECTED_OUTPUT = "### Expected output:"
    ACTUAL_OUTPUT = "### Actual output:"
    COMPILER_ERROR = "[COMPILER_ERROR] Check compile errors above."
    RUNTIME_ERROR = "[RUNTIME_ERROR] Check runtime errors above."
    CORRECT_ANSWER_FILE = StudentMessageStr(
        "[CORRECT_ANSWER] Output matches expected for std output of file {file_name}."
    )
    CORRECT_ANSWER_FUNCTION = StudentMessageStr(
        "[CORRECT_ANSWER] Output matches expected for return of function '{function_name}'."
    )
    WRONG_ANSWER_FILE = StudentMessageStr(
        "[WRONG_ANSWER] Output mismatch for for std output of file '{file_name}'."
    )
    WRONG_ANSWER_FUNCTION = StudentMessageStr(
        "[WRONG_ANSWER] Output mismatch for return of function '{function_name}'."
    )
    TIME_LIMIT_EXCEEDED_FILE = StudentMessageStr(
        "[TIME_LIMIT_EXCEEDED] timed out after {seconds} for {file_name}."
    )
    TIME_LIMIT_EXCEEDED_FUNCTION = StudentMessageStr(
        "[TIME_LIMIT_EXCEEDED] timed out after {seconds} for function {function_name}."
    )
    CORRECT_FILE = StudentMessageStr("[CORRECT_FILE] File '{file_name}' exists.")
    WRONG_FILE = StudentMessageStr("[WRONG_FILE] File '{file_name}' not found.")
    ERROR_FUNCTION_NOT_CALLABLE = StudentMessageStr(
        "Error: Function '{function_name}' is not callable"
    )
    CORRECT_SIGNATURE = StudentMessageStr(
        "[CORRECT_ANSWER] Function '{function_name}' signature is correct"
    )
    CORRECT_GITLAB_SUBMISSION = "[CORRECT_ANSWER] GitLab repository was found."
    WRONG_GITLAB_NOT_USED = "[WRONG_ANSWER] GitLab repository was not found."
