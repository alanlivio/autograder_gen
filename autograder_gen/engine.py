import os
import shutil
import zipfile
import tempfile
from typing import Optional, List, Dict, Any
import yaml
import json
import re
from types import SimpleNamespace
from pathlib import Path
from io import BytesIO, StringIO
import csv
from docx import Document
from docx.shared import Pt
from jinja2 import Environment, FileSystemLoader, select_autoescape
from autograder_gen.config import Config
from autograder_gen.engine_utils import print_error, print_success, print_warning


class Engine:
    """Generates Gradescope autograder packages from configuration using Jinja templates."""

    def __init__(self, config: Config, original_config_dict: Optional[dict] = None):
        """
        Initialize generator with configuration.
        Args:
            config: Config object
            original_config_dict: Optional dictionary of original unparsed YAML configuration
        """
        self.config = config
        self.original_config_dict = original_config_dict
        self.temp_dir: Optional[Path] = None
        self.templates_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(self, output_dir: str) -> str:
        """Generate the autograder.zip file using Jinja templates."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        self.temp_dir = output_path / "temp_autograder"
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir()
        tests_dir = self.temp_dir / "tests"
        tests_dir.mkdir()
        try:
            self._generate_setup_sh()
            self._generate_run_autograder()
            self._generate_run_tests(tests_dir)
            self._generate_requirements_txt()
            self._generate_metadata_files()
            zip_path = output_path / "autograder.zip"
            self._create_zip(zip_path)
            verification = self.verify_autograder_zip(zip_path)
            for err in verification.get("errors", []):
                print_error(f"  [ERROR] {err}")
            for warn in verification.get("warnings", []):
                print_warning(f"  [WARNING] {warn}")
            docx_buffer = self.generate_description_docx()
            with open(output_path / "description.docx", "wb") as f:
                f.write(docx_buffer.getbuffer())
            md_buffer = self.generate_description_md()
            with open(output_path / "description.md", "wb") as f:
                f.write(md_buffer.getbuffer())
            rubric_buffer = self.generate_rubric_csv()
            with open(output_path / "rubric.csv", "wb") as f:
                f.write(rubric_buffer.getbuffer())
            correct_buffer = self.generate_correct_answer_zip()
            with open(output_path / "correct_answer.zip", "wb") as f:
                f.write(correct_buffer.getbuffer())
            wrong_buffer = self.generate_wrong_answer_zip()
            with open(output_path / "wrong_answer.zip", "wb") as f:
                f.write(wrong_buffer.getbuffer())
            return str(zip_path)
        finally:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)

    def verify_autograder_zip(self, zip_source: Any = None) -> Dict[str, Any]:
        """Verify structure and validity of an autograder.zip archive."""
        errors = []
        warnings = []
        checks = []
        try:
            if zip_source is None:
                if self.temp_dir and self.temp_dir.exists():
                    names = [
                        str(f.relative_to(self.temp_dir))
                        for f in self.temp_dir.rglob("*")
                        if f.is_file()
                    ]
                else:
                    return {
                        "valid": False,
                        "checks": [],
                        "errors": ["No zip source or temp directory found to verify"],
                        "warnings": [],
                        "total_files": 0,
                    }
            elif isinstance(zip_source, (str, Path)):
                with zipfile.ZipFile(zip_source, "r") as zf:
                    names = zf.namelist()
            elif isinstance(zip_source, BytesIO):
                with zipfile.ZipFile(zip_source, "r") as zf:
                    names = zf.namelist()
            elif isinstance(zip_source, bytes):
                with zipfile.ZipFile(BytesIO(zip_source), "r") as zf:
                    names = zf.namelist()
            else:
                names = zip_source.namelist() if hasattr(zip_source, "namelist") else []
            if "run_autograder" in names:
                checks.append("Found required executable script: run_autograder")
            else:
                errors.append("Missing required root script: run_autograder")
            if "setup.sh" in names:
                checks.append("Found environment setup script: setup.sh")
            if any(
                n.startswith("source/") or n.startswith("autograder/") or "/" in n for n in names
            ):
                checks.append("Archive contains valid folder structures")
            valid = len(errors) == 0
        except Exception as e:
            valid = False
            errors.append(f"Invalid ZIP archive format: {str(e)}")
            names = []
        return {
            "valid": valid,
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
            "total_files": len(names),
        }

    def generate_description_docx(self) -> BytesIO:
        """Generate a Word document containing the assessment description."""
        doc = Document()
        doc.add_heading("Assessment Description", 0)
        for i, question in enumerate(self.config.questions, 1):
            doc.add_heading(f"Question {i}: {question.name}", level=1)
            if hasattr(question, "description") and question.description:
                doc.add_paragraph(question.description)
            question_points = sum(
                item.total_mark for item in question.marking_items if item.type != "file_exists"
            )
            p = doc.add_paragraph()
            run = p.add_run(f"Total Points: {question_points}")
            run.bold = True
            doc.add_heading("Marking Items", level=2)
            visible_item_idx = 1
            for item in question.marking_items:
                if item.type == "file_exists":
                    continue
                item_name = getattr(item, "name", "") or f"Marking Item {visible_item_idx}"
                doc.add_heading(f"{visible_item_idx}. {item_name}", level=3)
                doc.add_paragraph(f"Points: {item.total_mark}")
                if item.type == "output_comparison":
                    doc.add_paragraph(
                        f"Requirement: Program must produce specific output for given input in '{item.target_file}'."
                    )
                    if item.expected_input:
                        doc.add_heading("Example Input:", level=4)
                        p = doc.add_paragraph()
                        run = p.add_run(item.expected_input)
                        run.font.name = "Courier New"
                    if item.expected_output:
                        doc.add_heading("Expected Output:", level=4)
                        p = doc.add_paragraph()
                        run = p.add_run(item.expected_output)
                        run.font.name = "Courier New"
                elif item.type == "signature_check":
                    doc.add_paragraph(
                        f"Requirement: Function '{item.function_name}' in '{item.target_file}' must have correct signature."
                    )
                elif item.type == "function_test":
                    doc.add_paragraph(
                        f"Requirement: Function '{item.function_name}' in '{item.target_file}' must pass unit tests."
                    )
                elif item.type == "gitlab_submission_exists":
                    doc.add_paragraph(
                        "Requirement: Submission must be made via a GitLab repository."
                    )
                elif item.type == "github_submission_exists":
                    doc.add_paragraph(
                        "Requirement: Submission must be made via a GitHub repository."
                    )
                visible_item_idx += 1
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer

    def generate_description_md(self) -> BytesIO:
        lines = ["# Assessment Description", ""]
        for i, question in enumerate(self.config.questions, 1):
            lines.append(f"## Question {i}: {question.name}")
            lines.append("")
            if hasattr(question, "description") and question.description:
                lines.append(question.description)
                lines.append("")
            question_points = sum(
                item.total_mark for item in question.marking_items if item.type != "file_exists"
            )
            lines.append(f"**Total Points:** {question_points}")
            lines.append("")
            lines.append("### Marking Items")
            lines.append("")
            visible_item_idx = 1
            for item in question.marking_items:
                if item.type == "file_exists":
                    continue
                item_name = getattr(item, "name", "") or f"Marking Item {visible_item_idx}"
                lines.append(f"#### {visible_item_idx}. {item_name}")
                lines.append("")
                lines.append(f"- **Points:** {item.total_mark}")
                if item.type == "output_comparison":
                    lines.append(
                        f"- **Requirement:** Program must produce specific output for given input in `{item.target_file}`."
                    )
                    if item.expected_input:
                        lines.append("")
                        lines.append("##### Example Input:")
                        lines.append("```")
                        lines.append(item.expected_input)
                        lines.append("```")
                    if item.expected_output:
                        lines.append("")
                        lines.append("##### Expected Output:")
                        lines.append("```")
                        lines.append(item.expected_output)
                        lines.append("```")
                elif item.type == "signature_check":
                    lines.append(
                        f"- **Requirement:** Function `{item.function_name}` in `{item.target_file}` must have correct signature."
                    )
                elif item.type == "function_test":
                    lines.append(
                        f"- **Requirement:** Function `{item.function_name}` in `{item.target_file}` must pass unit tests."
                    )
                elif item.type == "gitlab_submission_exists":
                    lines.append(
                        "- **Requirement:** Submission must be made via a GitLab repository."
                    )
                elif item.type == "github_submission_exists":
                    lines.append(
                        "- **Requirement:** Submission must be made via a GitHub repository."
                    )
                lines.append("")
                visible_item_idx += 1
        md_content = "\n".join(lines).strip() + "\n"
        buffer = BytesIO(md_content.encode("utf-8"))
        buffer.seek(0)
        return buffer

    def generate_description_html(self) -> BytesIO:
        summary = self.config.get_config_summary()
        html_lines = [
            "<!DOCTYPE html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="UTF-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f"  <title>Assessment Description - {self.config.language.capitalize()}</title>",
            "  <style>",
            "    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; max-width: 900px; margin: 0 auto; padding: 2rem; background: #f8fafc; }",
            "    .header { background: #ffffff; padding: 2rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 2rem; border-top: 4px solid #475569; }",
            "    h1 { margin-top: 0; color: #0f172a; }",
            "    .meta-badge { display: inline-block; background: #e2e8f0; color: #334155; padding: 0.25rem 0.75rem; border-radius: 9999px; font-weight: 600; font-size: 0.875rem; margin-right: 0.5rem; }",
            "    .question-card { background: #ffffff; padding: 1.5rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 1.5rem; }",
            "    .question-title { color: #1e293b; margin-top: 0; display: flex; justify-content: space-between; align-items: center; }",
            "    .points-tag { background: #f1f5f9; border: 1px solid #cbd5e1; color: #475569; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 600; font-size: 0.875rem; }",
            "    .item-block { border-left: 3px solid #94a3b8; padding-left: 1rem; margin: 1rem 0; }",
            "    pre { background: #0f172a; color: #f8fafc; padding: 1rem; border-radius: 6px; overflow-x: auto; font-family: 'Fira Code', 'Courier New', monospace; font-size: 0.9rem; }",
            "    code { font-family: 'Fira Code', 'Courier New', monospace; background: #e2e8f0; padding: 0.2rem 0.4rem; border-radius: 4px; font-size: 0.9em; }",
            "  </style>",
            "</head>",
            "<body>",
            '  <div class="header">',
            "    <h1>Assessment Description</h1>",
            "    <div>",
            f'      <span class="meta-badge">Language: {summary["language"].capitalize()}</span>',
            f'      <span class="meta-badge">Total Marks: {summary["total_marks"]}</span>',
            f'      <span class="meta-badge">Questions: {summary["total_questions"]}</span>',
            f'      <span class="meta-badge">Time Limit: {summary["global_time_limit"]}s</span>',
            "    </div>",
            "  </div>",
        ]
        for i, question in enumerate(self.config.questions, 1):
            question_points = sum(
                item.total_mark for item in question.marking_items if item.type != "file_exists"
            )
            html_lines.append('  <div class="question-card">')
            html_lines.append('    <div class="question-title">')
            html_lines.append(f"      <h2>Question {i}: {question.name}</h2>")
            html_lines.append(f'      <span class="points-tag">{question_points} pts</span>')
            html_lines.append("    </div>")
            if hasattr(question, "description") and question.description:
                html_lines.append(f"    <p>{question.description}</p>")
            html_lines.append("    <h3>Marking Items</h3>")
            visible_item_idx = 1
            for item in question.marking_items:
                if item.type == "file_exists":
                    continue
                item_name = getattr(item, "name", "") or f"Marking Item {visible_item_idx}"
                html_lines.append('    <div class="item-block">')
                html_lines.append(
                    f"      <h4>{visible_item_idx}. {item_name} ({item.total_mark} pts)</h4>"
                )
                if item.type == "output_comparison":
                    html_lines.append(
                        f"      <p><strong>Requirement:</strong> Program must produce specific output for target file <code>{item.target_file}</code>.</p>"
                    )
                    if item.expected_input:
                        html_lines.append("      <p><strong>Example Input:</strong></p>")
                        html_lines.append(f"      <pre>{item.expected_input}</pre>")
                    if item.expected_output:
                        html_lines.append("      <p><strong>Expected Output:</strong></p>")
                        html_lines.append(f"      <pre>{item.expected_output}</pre>")
                elif item.type == "signature_check":
                    html_lines.append(
                        f"      <p><strong>Requirement:</strong> Function <code>{item.function_name}</code> in <code>{item.target_file}</code> must match signature.</p>"
                    )
                elif item.type == "function_test":
                    html_lines.append(
                        f"      <p><strong>Requirement:</strong> Function <code>{item.function_name}</code> in <code>{item.target_file}</code> must pass unit tests.</p>"
                    )
                elif item.type == "gitlab_submission_exists":
                    html_lines.append(
                        "      <p><strong>Requirement:</strong> Submission must be made via a GitLab repository.</p>"
                    )
                elif item.type == "github_submission_exists":
                    html_lines.append(
                        "      <p><strong>Requirement:</strong> Submission must be made via a GitHub repository.</p>"
                    )
                html_lines.append("    </div>")
                visible_item_idx += 1
            html_lines.append("  </div>")
        html_lines.extend(["</body>", "</html>"])
        html_content = "\n".join(html_lines) + "\n"
        buffer = BytesIO(html_content.encode("utf-8"))
        buffer.seek(0)
        return buffer

    def generate_correct_answer_zip(self) -> BytesIO:
        """Generate a ZIP file with correct implementation skeletons."""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            created_dirs = set()
            for filename in self.config.files_necessary:
                parent = Path(filename).parent
                if str(parent) != "." and str(parent) not in created_dirs:
                    created_dirs.add(str(parent))
                    zipf.writestr(f"{parent}/", "")
                content = self._generate_skeleton_content(filename, correct=True)
                zipf.writestr(filename, content)

            has_gitlab = any(
                item.type == "gitlab_submission_exists"
                for q in self.config.questions
                for item in q.marking_items
            )
            has_github = any(
                item.type == "github_submission_exists"
                for q in self.config.questions
                for item in q.marking_items
            )
            if has_gitlab:
                zipf.writestr(
                    "submission_metadata.json",
                    json.dumps({"submission_method": "GitLab"}),
                )
            elif has_github:
                zipf.writestr(
                    "submission_metadata.json",
                    json.dumps({"submission_method": "GitHub"}),
                )
        buffer.seek(0)
        return buffer

    def generate_wrong_answer_zip(self) -> BytesIO:
        """Generate a ZIP file with incorrect implementation skeletons."""
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            created_dirs = set()
            for filename in self.config.files_necessary:
                parent = Path(filename).parent
                if str(parent) != "." and str(parent) not in created_dirs:
                    created_dirs.add(str(parent))
                    zipf.writestr(f"{parent}/", "")
                content = self._generate_skeleton_content(filename, correct=False)
                zipf.writestr(filename, content)
        buffer.seek(0)
        return buffer

    def generate_rubric_md(self) -> BytesIO:
        """Generate a Markdown document containing the assessment grading rubric matrix."""
        summary = self.config.get_config_summary()
        lines = [
            "# Assessment Grading Rubric Matrix",
            "",
            "## Overview",
            f"- **Language:** {summary['language']}",
            f"- **Global Time Limit:** {summary['global_time_limit']}s",
            f"- **Total Questions:** {summary['total_questions']}",
            f"- **Total Marking Items:** {summary['total_marking_items']}",
            f"- **Total Marks:** {summary['total_marks']}",
            "",
            "## Detailed Rubric Matrix",
            "",
            "| Question | Marking Item | Type | Target File | Marks | Time Limit | Visibility |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for q in self.config.questions:
            for idx, item in enumerate(q.marking_items, 1):
                item_name = getattr(item, "name", "") or f"Item {idx}"
                lines.append(
                    f"| {q.name} | {item_name} | {item.type} | {item.target_file} | {item.total_mark} | {item.time_limit}s | {item.visibility} |"
                )
        lines.append("")
        content = "\n".join(lines)
        buffer = BytesIO(content.encode("utf-8"))
        buffer.seek(0)
        return buffer

    def generate_rubric_csv(self) -> BytesIO:
        """Generate a CSV document containing the assessment grading rubric matrix."""
        s_io = StringIO()
        writer = csv.writer(s_io)
        writer.writerow(
            [
                "Question",
                "Marking Item",
                "Type",
                "Target File",
                "Marks",
                "Time Limit",
                "Visibility",
            ]
        )
        for q in self.config.questions:
            for idx, item in enumerate(q.marking_items, 1):
                item_name = getattr(item, "name", "") or f"Item {idx}"
                writer.writerow(
                    [
                        q.name,
                        item_name,
                        item.type,
                        item.target_file,
                        item.total_mark,
                        item.time_limit,
                        item.visibility,
                    ]
                )
        content = s_io.getvalue()
        buffer = BytesIO(content.encode("utf-8"))
        buffer.seek(0)
        return buffer

    def _generate_skeleton_content(self, target_file: str, correct: bool = True) -> str:
        import ast

        def get_python_literal_str(expected_str: str) -> str:
            try:
                val = ast.literal_eval(expected_str)
                return repr(val)
            except Exception:
                return repr(expected_str)

        def get_java_literal_str(expected_str: str) -> str:
            val_strip = expected_str.strip()
            if val_strip == "True":
                return "true"
            if val_strip == "False":
                return "false"
            if val_strip == "None":
                return "null"
            try:
                int(val_strip)
                return val_strip
            except ValueError:
                pass
            try:
                float(val_strip)
                return val_strip
            except ValueError:
                pass
            escaped = expected_str.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'

        if target_file.endswith(".pdf"):
            return ""

        if self.config.language == "python":
            lines = ["# Skeleton for " + target_file, ""]
            functions = set()
            for q in self.config.questions:
                for item in q.marking_items:
                    if item.target_file == target_file:
                        if hasattr(item, "function_name") and item.function_name:
                            functions.add(item.function_name)
            for func in sorted(functions):
                expected_params = ""
                expected_return = ""
                for q in self.config.questions:
                    for item in q.marking_items:
                        if (
                            item.target_file == target_file
                            and getattr(item, "function_name", "") == func
                        ):
                            if getattr(item, "expected_parameters", "") and not expected_params:
                                expected_params = item.expected_parameters.strip()
                            if getattr(item, "expected_return_type", "") and not expected_return:
                                expected_return = item.expected_return_type.strip()

                param_names = []
                if expected_params:
                    for part in expected_params.split(","):
                        name = part.split(":")[0].split("=")[0].strip()
                        if name:
                            param_names.append(name)

                if correct and expected_params:
                    ret_anno = f" -> {expected_return}" if expected_return else ""
                    lines.append(f"def {func}({expected_params}){ret_anno}:")
                else:
                    lines.append(f"def {func}(*args, **kwargs):")

                if correct:
                    cases = []
                    for q in self.config.questions:
                        for item in q.marking_items:
                            if (
                                item.target_file == target_file
                                and getattr(item, "function_name", "") == func
                                and item.type == "function_test"
                            ):
                                if hasattr(item, "test_cases") and item.test_cases:
                                    for tc in item.test_cases:
                                        cases.append(tc)
                    if cases:
                        for tc in cases:
                            conds = []
                            args_list = tc.get("args", []) or []
                            kwargs_dict = tc.get("kwargs", {}) or {}
                            if expected_params and param_names:
                                for idx, arg_val in enumerate(args_list):
                                    if idx < len(param_names):
                                        conds.append(f"{param_names[idx]} == {repr(arg_val)}")
                                for k, v in kwargs_dict.items():
                                    if k in param_names:
                                        conds.append(f"{k} == {repr(v)}")
                            else:
                                if args_list:
                                    conds.append(f"args == {tuple(args_list)}")
                                else:
                                    conds.append("not args")
                                if kwargs_dict:
                                    conds.append(f"kwargs == {kwargs_dict}")
                                else:
                                    conds.append("not kwargs")
                            cond_str = " and ".join(conds) if conds else "True"
                            expected_val = tc.get("expected", "")
                            expr = get_python_literal_str(expected_val)
                            lines.append(f"    if {cond_str}:")
                            lines.append(f"        return {expr}")
                        lines.append("    pass")
                    else:
                        lines.append("    pass")
                else:
                    lines.append("    return None")
                lines.append("")
            output_items = []
            for q in self.config.questions:
                for item in q.marking_items:
                    if item.target_file == target_file and item.type == "output_comparison":
                        output_items.append(item)

            if output_items:
                lines.append('if __name__ == "__main__":')
                if correct:
                    lines.append("    import sys")
                    lines.append("    _raw_in = sys.stdin.read()")
                    lines.append("    _in = _raw_in.strip()")
                    for idx, item in enumerate(output_items):
                        cond = f"_in == {repr(item.expected_input.strip())}"
                        out_val = item.expected_output
                        branch = "if" if idx == 0 else "elif"
                        lines.append(f"    {branch} {cond}:")
                        lines.append(f"        sys.stdout.write({repr(out_val)})")
                        lines.append("        sys.exit(0)")
                    default_out = output_items[0].expected_output if output_items else ""
                    lines.append("    else:")
                    lines.append(f"        sys.stdout.write({repr(default_out)})")
                else:
                    lines.append("    pass")
                lines.append("")

            if not functions and not output_items:
                lines.append("# No specific functions defined for this file.")
                if not correct:
                    lines.append("# This file might be intentionally wrong or missing logic.")
            return "\n".join(lines)
        elif self.config.language == "java":
            import json

            class_name = Path(target_file).stem
            lines = [
                "import java.util.*;",
                "import java.nio.file.*;",
                "",
                f"public class {class_name} {{",
                "",
            ]
            functions = set()
            for q in self.config.questions:
                for item in q.marking_items:
                    if item.target_file == target_file:
                        if hasattr(item, "function_name") and item.function_name:
                            functions.add(item.function_name)

            def _infer_java_type(val, desc=""):
                if isinstance(val, bool) or (str(val).lower() in ("true", "false") and not isinstance(val, (int, float))):
                    return "boolean"
                if isinstance(val, int):
                    return "long" if abs(val) > 2147483647 else "int"
                if isinstance(val, float):
                    return "double"
                if isinstance(val, list):
                    if val and isinstance(val[0], list):
                        return "double[][]" if any("." in str(x) for row in val for x in row) else "int[][]"
                    is_arraylist = "arraylist" in desc.lower() or "list" in desc.lower()
                    has_strings = any(
                        isinstance(x, str) and not x.strip().lstrip("-").isdigit()
                        for x in val
                    )
                    if has_strings or any(isinstance(x, str) for x in val):
                        if is_arraylist:
                            return "java.util.ArrayList<String>"
                        return "String[]"
                    if is_arraylist:
                        return "java.util.ArrayList<Double>" if any("." in str(x) for x in val) else "java.util.ArrayList<Integer>"
                    return "double[]" if any("." in str(x) for x in val) else "int[]"
                s = str(val).strip()
                if (s.startswith("{{") and s.endswith("}}")) or (s.startswith("[[") and s.endswith("]]")):
                    return "double[][]" if "." in s else "int[][]"
                if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
                    is_arraylist = "arraylist" in desc.lower() or "list" in desc.lower()
                    inner = s[1:-1].strip()
                    has_letters = any(c.isalpha() for c in inner)
                    if has_letters:
                        if is_arraylist:
                            return "java.util.ArrayList<String>"
                        return "String[]"
                    if is_arraylist:
                        return "java.util.ArrayList<Double>" if "." in inner else "java.util.ArrayList<Integer>"
                    return "double[]" if "." in s else "int[]"
                try:
                    v_int = int(s)
                    return "long" if abs(v_int) > 2147483647 else "int"
                except ValueError:
                    try:
                        float(s)
                        return "double"
                    except ValueError:
                        return "String"

            for func in sorted(functions):
                func_items = [
                    item
                    for q in self.config.questions
                    for item in q.marking_items
                    if item.target_file == target_file and getattr(item, "function_name", "") == func
                ]
                desc_text = " ".join([
                    getattr(item, "description", "")
                    for item in func_items
                ] + [
                    getattr(item, "name", "")
                    for item in func_items
                ] + [
                    getattr(q, "description", "")
                    for q in self.config.questions
                    for item in q.marking_items
                    if item in func_items
                ])
                cases = []
                for item in func_items:
                    for tc in getattr(item, "test_cases", []) or []:
                        cases.append(tc)

                max_args = 0
                for tc in cases:
                    args_len = len(tc.get("args", []) or [])
                    if args_len > max_args:
                        max_args = args_len

                param_types = []
                for i in range(max_args):
                    arg_vals = [tc.get("args", [])[i] for tc in cases if len(tc.get("args", []) or []) > i]
                    ptype = _infer_java_type(arg_vals[0], desc_text) if arg_vals else "Object"
                    param_types.append(ptype)

                param_names = [chr(97 + i) for i in range(max_args)]
                param_str = ", ".join(f"{pt} {pn}" for pt, pn in zip(param_types, param_names))

                ret_type = "double"
                if cases:
                    exp0 = str(cases[0].get("expected", ""))
                    if "\n" in exp0:
                        ret_type = "void"
                    elif ("arraylist" in desc_text.lower() or "list" in desc_text.lower()) and ((exp0.startswith("[") and exp0.endswith("]")) or (exp0.startswith("{") and exp0.endswith("}"))):
                        inner = exp0[1:-1].strip()
                        if any(c.isalpha() for c in inner) or not inner:
                            ret_type = "java.util.ArrayList<String>"
                        elif "." in inner:
                            ret_type = "java.util.ArrayList<Double>"
                        else:
                            ret_type = "java.util.ArrayList<Integer>"
                    elif (exp0.startswith("[") and exp0.endswith("]")) or (exp0.startswith("{") and exp0.endswith("}")):
                        inner = exp0[1:-1].strip()
                        if any(c.isalpha() for c in inner):
                            ret_type = "String[]"
                        elif "." in exp0:
                            ret_type = "double[]"
                        else:
                            ret_type = "int[]"
                    elif exp0.strip().lower() in ("true", "false"):
                        ret_type = "boolean"
                    else:
                        try:
                            v_int = int(exp0.strip())
                            ret_type = "long" if abs(v_int) > 2147483647 else "int"
                        except ValueError:
                            try:
                                float(exp0.strip())
                                ret_type = "double"
                            except ValueError:
                                ret_type = "String"

                if func == "add" and max_args == 2:
                    lines.append(f"    public static double {func}(double a, double b) {{")
                    if correct:
                        lines.append("        return a + b;")
                    else:
                        lines.append("        return 0.0;")
                    lines.append("    }")
                    lines.append("")
                    continue

                lines.append(f"    public static {ret_type} {func}({param_str}) {{")
                if correct:
                    for tc in cases:
                        args_list = tc.get("args", []) or []
                        cond_parts = []
                        for idx, arg_val in enumerate(args_list):
                            pn = param_names[idx]
                            pt = param_types[idx]
                            if pt == "double":
                                try:
                                    cond_parts.append(f"Math.abs({pn} - {float(arg_val)}) < 1e-4")
                                except Exception:
                                    cond_parts.append(f"{pn} == {arg_val}")
                            elif pt in ("int", "long"):
                                cond_parts.append(f"{pn} == {arg_val}")
                            elif pt == "boolean":
                                cond_parts.append(f"{pn} == {str(arg_val).lower()}")
                            elif pt == "String":
                                cond_parts.append(f"{pn} != null && {pn}.equals({json.dumps(str(arg_val))})")
                            elif pt == "java.util.ArrayList<String>":
                                if isinstance(arg_val, list):
                                    items_code = ", ".join(json.dumps(str(x)) for x in arg_val)
                                else:
                                    raw = str(arg_val).strip().lstrip("[").rstrip("]").strip()
                                    items = [x.strip().strip("'\"") for x in raw.split(",") if x.strip()]
                                    items_code = ", ".join(json.dumps(x) for x in items)
                                cond_parts.append(f"{pn} != null && {pn}.equals(new java.util.ArrayList<>(java.util.Arrays.asList({items_code})))")
                            elif pt == "String[]":
                                if isinstance(arg_val, list):
                                    items_code = ", ".join(json.dumps(str(x)) for x in arg_val)
                                else:
                                    raw = str(arg_val).strip().lstrip("[").rstrip("]").strip()
                                    items = [x.strip().strip("'\"") for x in raw.split(",") if x.strip()]
                                    items_code = ", ".join(json.dumps(x) for x in items)
                                cond_parts.append(f"java.util.Arrays.equals({pn}, new String[]{{{items_code}}})")
                            elif pt.endswith("[][]"):
                                raw_s = str(arg_val).strip()
                                if raw_s.startswith("["):
                                    raw_s = raw_s.replace("[", "{").replace("]", "}")
                                cond_parts.append(f"java.util.Arrays.deepEquals({pn}, new {pt}{raw_s})")
                            elif pt.endswith("[]"):
                                raw_s = str(arg_val).strip()
                                if raw_s.startswith("["):
                                    raw_s = raw_s.replace("[", "{").replace("]", "}")
                                cond_parts.append(f"java.util.Arrays.equals({pn}, new {pt}{raw_s})")

                        cond = " && ".join(cond_parts) if cond_parts else "true"
                        exp_val = tc.get("expected", "")
                        if ret_type == "void":
                            lines.append(f"        if ({cond}) {{")
                            lines.append(f"            System.out.print({json.dumps(str(exp_val))});")
                            lines.append("            try {")
                            lines.append(f"                java.nio.file.Files.writeString(java.nio.file.Path.of(\"sortComparison.csv\"), {json.dumps(str(exp_val))});")
                            lines.append("            } catch (Exception e) {}")
                            lines.append("            return;")
                            lines.append("        }")
                        elif ret_type == "java.util.ArrayList<String>":
                            if isinstance(exp_val, list):
                                items = [str(x) for x in exp_val]
                            else:
                                raw = str(exp_val).strip().lstrip("[").rstrip("]").strip()
                                items = [x.strip().strip("'\"") for x in raw.split(",") if x.strip()]
                            items_code = ", ".join(json.dumps(x) for x in items)
                            lines.append(f"        if ({cond}) {{")
                            lines.append(f"            return new java.util.ArrayList<>(java.util.Arrays.asList({items_code}));")
                            lines.append("        }")
                        elif ret_type == "String[]":
                            if isinstance(exp_val, list):
                                items = [str(x) for x in exp_val]
                            else:
                                raw = str(exp_val).strip().lstrip("[").rstrip("]").strip()
                                items = [x.strip().strip("'\"") for x in raw.split(",") if x.strip()]
                            items_code = ", ".join(json.dumps(x) for x in items)
                            lines.append(f"        if ({cond}) {{")
                            lines.append(f"            return new String[]{{{items_code}}};")
                            lines.append("        }")
                        elif ret_type.endswith("[]"):
                            raw_e = str(exp_val).strip()
                            if raw_e.startswith("["):
                                raw_e = raw_e.replace("[", "{").replace("]", "}")
                            lines.append(f"        if ({cond}) {{")
                            lines.append(f"            return new {ret_type}{raw_e};")
                            lines.append("        }")
                        elif ret_type == "double":
                            lines.append(f"        if ({cond}) {{")
                            lines.append(f"            return {float(exp_val)};")
                            lines.append("        }")
                        elif ret_type in ("int", "long"):
                            lines.append(f"        if ({cond}) {{")
                            lines.append(f"            return {int(exp_val)};")
                            lines.append("        }")
                        elif ret_type == "boolean":
                            lines.append(f"        if ({cond}) {{")
                            lines.append(f"            return {str(exp_val).lower()};")
                            lines.append("        }")
                        else:
                            lines.append(f"        if ({cond}) {{")
                            lines.append(f"            return {json.dumps(str(exp_val))};")
                            lines.append("        }")

                    if ret_type == "void":
                        pass
                    elif ret_type == "double":
                        lines.append("        return 0.0;")
                    elif ret_type == "int":
                        lines.append("        return 0;")
                    elif ret_type == "long":
                        lines.append("        return 0L;")
                    elif ret_type == "boolean":
                        lines.append("        return false;")
                    elif ret_type == "java.util.ArrayList<String>":
                        lines.append("        return new java.util.ArrayList<>();")
                    elif ret_type.endswith("[]"):
                        lines.append(f"        return new {ret_type[:-2]}[0];")
                    else:
                        lines.append('        return "";')
                else:
                    if ret_type == "void":
                        lines.append('        System.out.print("wrong_output");')
                    elif ret_type == "double":
                        lines.append("        return -999999.0;")
                    elif ret_type == "int":
                        lines.append("        return -999999;")
                    elif ret_type == "long":
                        lines.append("        return -999999L;")
                    elif ret_type == "boolean":
                        has_false = any(str(tc.get("expected", "")).strip().lower() == "false" for tc in cases)
                        lines.append(f"        return {'true' if has_false else 'false'};")
                    elif ret_type == "java.util.ArrayList<String>":
                        lines.append("        return new java.util.ArrayList<>();")
                    elif ret_type.endswith("[]"):
                        lines.append("        return null;")
                    else:
                        lines.append('        return "wrong_answer";')
                lines.append("    }")
                lines.append("")

            output_items = [
                item
                for q in self.config.questions
                for item in q.marking_items
                if item.target_file == target_file and item.type == "output_comparison"
            ]
            if output_items:
                lines.append("    public static void main(String[] args) {")
                if correct:
                    lines.append("        java.util.Scanner sc = new java.util.Scanner(System.in);")
                    lines.append("        StringBuilder sb = new StringBuilder();")
                    lines.append("        while (sc.hasNextLine()) {")
                    lines.append("            sb.append(sc.nextLine()).append(\"\\n\");")
                    lines.append("        }")
                    lines.append("        String inStr = sb.toString().trim();")
                    for idx, item in enumerate(output_items):
                        cond = f"inStr.equals({json.dumps(item.expected_input.strip())})"
                        branch = "if" if idx == 0 else "else if"
                        lines.append(f"        {branch} ({cond}) {{")
                        lines.append(f"            System.out.print({json.dumps(item.expected_output)});")
                        lines.append("            return;")
                        lines.append("        }")
                    default_out = output_items[0].expected_output if output_items else ""
                    lines.append("        else {")
                    lines.append(f"            System.out.print({json.dumps(default_out)});")
                    lines.append("        }")
                lines.append("    }")
                lines.append("")

            lines.append("}")
            return "\n".join(lines)

        return "# Skeleton for " + target_file

    def _generate_setup_sh(self):
        """Generate setup.sh using Jinja template."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"

        template = self.jinja_env.get_template("setup.sh.j2")
        content = template.render(config=self.config)

        setup_file = self.temp_dir / "setup.sh"
        with open(setup_file, "w", encoding="utf-8") as f:
            f.write(content)

        os.chmod(setup_file, 0o755)

    def _generate_run_autograder(self):
        """Generate run_autograder using Jinja template."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"
        template = self.jinja_env.get_template("run_autograder.j2")
        content = template.render(config=self.config)

        for filename in ("run_autograder", "run_autograder.sh"):
            filepath = self.temp_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
            os.chmod(filepath, 0o755)

    def _generate_run_tests(self, tests_dir: Path):
        """Generate modular test files: main run_tests.py and individual question test files."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"
        template = self.jinja_env.get_template("run_tests.py.j2")
        content = template.render(config=self.config)

        run_tests_file = self.temp_dir / "run_tests.py"
        with open(run_tests_file, "w", encoding="utf-8") as f:
            f.write(content)

        grader_utils_src = Path(__file__).parent / "grader_utils.py"
        if grader_utils_src.exists():
            shutil.copy2(grader_utils_src, self.temp_dir / "grader_utils.py")
            shutil.copy2(grader_utils_src, tests_dir / "grader_utils.py")

        self._generate_question_test_files(tests_dir)

    def _generate_question_test_files(self, tests_dir: Path):
        """Generate individual test files for each question."""
        question_template = self.jinja_env.get_template("test_question.py.j2")

        for idx, question in enumerate(self.config.questions, 1):
            question_filename = f"question_{idx}"

            processed_question = self._preprocess_question_for_output_comparison(question)

            content = question_template.render(
                config=self.config, question=processed_question, question_number=idx
            )

            test_file = tests_dir / f"{question_filename}_test.py"
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)

    def _preprocess_question_for_output_comparison(self, question):
        """Preprocess question to add newlines to expected output for output comparison tests."""

        processed_question = SimpleNamespace()
        processed_question.name = question.name
        processed_question.marking_items = []

        for item in question.marking_items:
            processed_item = SimpleNamespace()
            for attr in dir(item):
                if not attr.startswith("_") and not attr.startswith("model_"):
                    setattr(processed_item, attr, getattr(item, attr))

            if (
                self.config.language == "python"
                and hasattr(processed_item, "type")
                and processed_item.type == "output_comparison"
                and hasattr(processed_item, "expected_output")
                and processed_item.expected_output
                and not processed_item.expected_output.endswith("\n")
            ):
                processed_item.expected_output += "\n"

            processed_question.marking_items.append(processed_item)

        return processed_question

    def _sanitize_filename(self, name: str) -> str:
        """Convert question name to a safe Python module filename."""
        safe_name = name.lower()
        safe_name = safe_name.replace(" ", "_")
        safe_name = safe_name.replace("-", "_")
        safe_name = safe_name.replace(".", "_")
        safe_name = safe_name.replace("(", "")
        safe_name = safe_name.replace(")", "")
        safe_name = safe_name.replace("[", "")
        safe_name = safe_name.replace("]", "")
        safe_name = safe_name.replace("/", "_")
        safe_name = safe_name.replace("\\", "_")
        safe_name = safe_name.replace(":", "_")
        safe_name = safe_name.replace(";", "_")
        safe_name = safe_name.replace(",", "_")
        safe_name = safe_name.replace("?", "_")
        safe_name = safe_name.replace("!", "_")
        safe_name = safe_name.replace("@", "_")
        safe_name = safe_name.replace("#", "_")
        safe_name = safe_name.replace("$", "_")
        safe_name = safe_name.replace("%", "_")
        safe_name = safe_name.replace("^", "_")
        safe_name = safe_name.replace("&", "_")
        safe_name = safe_name.replace("*", "_")
        safe_name = safe_name.replace("+", "_")
        safe_name = safe_name.replace("=", "_")
        safe_name = safe_name.replace("|", "_")
        safe_name = safe_name.replace("<", "_")
        safe_name = safe_name.replace(">", "_")

        safe_name = re.sub(r"_+", "_", safe_name)

        safe_name = safe_name.strip("_")

        if not safe_name or safe_name[0].isdigit():
            safe_name = "question_" + safe_name

        return safe_name

    def _generate_requirements_txt(self):
        """Generate requirements.txt using Jinja template."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"

        template = self.jinja_env.get_template("requirements.txt.j2")
        content = template.render(config=self.config)

        requirements_file = self.temp_dir / "requirements.txt"
        with open(requirements_file, "w", encoding="utf-8") as f:
            f.write(content)

    def _generate_metadata_files(self):
        """Generate metadata and configuration files."""
        assert self.temp_dir is not None, "temp_dir must be set before generating files"

        if self.original_config_dict:
            original_config_file = self.temp_dir / "autograder_gen.yaml"
            with open(original_config_file, "w", encoding="utf-8") as f:
                yaml.dump(
                    self.original_config_dict,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                )

        readme_content = f"""# Autograder Package

Generated by TIF Autograder Tool

## Configuration Summary
- **Language**: {self.config.language}
- **Questions**: {len(self.config.questions)}
- **Total Marking Items**: {sum(len(q.marking_items) for q in self.config.questions)}
- **Total Points**: {sum(sum(item.total_mark for item in q.marking_items) for q in self.config.questions)}
- **Required Files**: {', '.join(self.config.files_necessary) if self.config.files_necessary else 'None specified'}

## Package Structure
```
autograder.zip
├── setup.sh                 # Environment setup script
├── run_autograder          # Main autograder execution script
├── run_tests.py            # Primary test runner using gradescope-utils
├── requirements.txt        # Python dependencies
├── tests/                  # Individual test files for each question
│   ├── question_1_test.py
│   ├── question_2_test.py
│   └── ...
├── autograder_gen.yaml     # Original configuration file
└── README.md              # This file
```

## Test Types Supported
- **file_exists**: Checks if required files are present in submission
- **output_comparison**: Compares program output with expected results
- **signature_check**: Validates function signatures and parameters
- **function_test**: Tests function behavior with specific inputs and expected outputs

## Global Settings
- **Global Time Limit**: {getattr(self.config, 'global_time_limit', 'Not set')} seconds
- **Points Precision**: {getattr(self.config, 'points_precision', 1)} decimal place(s)

## Questions and Marking Items"""

        for i, question in enumerate(self.config.questions, 1):
            readme_content += f"\n\n### Question {i}: {question.name}\n"

            question_points = sum(item.total_mark for item in question.marking_items)
            readme_content += f"**Total Points**: {question_points}\n\n"

            for j, item in enumerate(question.marking_items, 1):
                item_name = getattr(item, "name", "") or f"Marking Item {j}"
                readme_content += f"#### {j}. {item_name}\n"
                readme_content += f"- **Type**: {item.type.replace('_', ' ').title()}\n"
                readme_content += f"- **Target File**: {item.target_file}\n"
                readme_content += f"- **Points**: {item.total_mark}\n"

                if hasattr(item, "time_limit") and item.time_limit:
                    readme_content += f"- **Time Limit**: {item.time_limit} seconds\n"

                if hasattr(item, "visibility") and item.visibility:
                    visibility_map = {
                        "hidden": "Hidden from students",
                        "visible": "Visible to students immediately",
                        "after_due_date": "Visible after due date",
                        "after_published": "Visible after grades published",
                    }
                    readme_content += f"- **Visibility**: {visibility_map.get(item.visibility, item.visibility)}\n"

                if item.type == "function_test":
                    if hasattr(item, "function_name") and item.function_name:
                        readme_content += f"- **Function**: `{item.function_name}()`\n"
                    if hasattr(item, "test_cases") and item.test_cases:
                        readme_content += f"- **Test Cases**: {len(item.test_cases)} case(s)\n"

                elif item.type == "signature_check":
                    if hasattr(item, "function_name") and item.function_name:
                        readme_content += f"- **Function**: `{item.function_name}()`\n"
                    if hasattr(item, "expected_parameters") and item.expected_parameters:
                        readme_content += (
                            f"- **Expected Parameters**: `{item.expected_parameters}`\n"
                        )

                elif item.type == "output_comparison":
                    if hasattr(item, "expected_input") and item.expected_input:
                        input_lines = item.expected_input.count("\n") + 1
                        readme_content += f"- **Input Lines**: {input_lines}\n"
                    if hasattr(item, "expected_output") and item.expected_output:
                        output_lines = item.expected_output.count("\n") + 1
                        readme_content += f"- **Expected Output Lines**: {output_lines}\n"

                elif item.type == "gitlab_submission_exists":
                    readme_content += (
                        "- **Requirement**: Submission must be made via a GitLab repository\n"
                    )
                elif item.type == "github_submission_exists":
                    readme_content += (
                        "- **Requirement**: Submission must be made via a GitHub repository\n"
                    )

                readme_content += "\n"

        readme_content += f"""
## Execution Details

### Setup Process
1. **Environment Setup**: `setup.sh` installs required packages and prepares the testing environment
2. **Test Execution**: `run_autograder` executes `run_tests.py` which runs all question test files
3. **Results Collection**: Results are formatted using gradescope-utils and written to `/autograder/results/results.json`

### File Requirements
Students must submit the following files:
"""

        if self.config.files_necessary:
            for file in self.config.files_necessary:
                readme_content += f"- `{file}`\n"
        else:
            readme_content += "- No specific files required (will be determined by marking items)\n"

        readme_content += f"""
### Points Distribution
"""

        for i, question in enumerate(self.config.questions, 1):
            question_points = sum(item.total_mark for item in question.marking_items)
            readme_content += f"- **Question {i}**: {question_points} points\n"

        total_points = sum(
            sum(item.total_mark for item in q.marking_items) for q in self.config.questions
        )
        readme_content += f"- **Total Possible**: {total_points} points\n"

        readme_content += f"""
## Technical Notes

- Generated using TIF Autograder Tool
- Uses gradescope-utils for test framework compatibility
- Supports Python {self.config.language} submissions
- All tests run in isolated environments with proper timeout handling
- Results are automatically formatted for Gradescope integration

For questions about this autograder configuration, refer to the original `autograder_gen.yaml` file included in this package.
"""

        readme_file = self.temp_dir / "README.md"
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(readme_content)

    def _create_zip(self, zip_path: Path):
        """Create the autograder.zip file with proper structure."""
        assert self.temp_dir is not None, "temp_dir must be set before creating zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_path in self.temp_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.temp_dir)
                    zipf.write(file_path, arcname)
