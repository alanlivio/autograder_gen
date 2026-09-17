from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import yaml

from autograder_gen.config import Config
from autograder_gen.engine import Engine


class AutograderRunner:
    def __init__(
        self,
        config_src: str | Path | Config | dict[str, Any],
        *,
        autograder_root: str | Path | None = None,
        python_path: str | None = None,
        timeout: int | float | None = None,
        env: dict[str, str] | None = None,
        save_log: bool = True,
        verbose: bool = False,
    ):
        self.config_src = config_src
        self.config = config_src
        self.autograder_root = autograder_root
        self.python_path = python_path
        self.timeout = timeout
        self.env = env
        self.save_log = save_log
        self.verbose = verbose
        self._cached_zip_bytes: bytes | None = None
        self._cached_correct_zip_bytes: bytes | None = None
        self._cached_wrong_zip_bytes: bytes | None = None

    @property
    def config_obj(self) -> Config | None:
        if isinstance(self.config, Config):
            return self.config
        if isinstance(self.config, (str, Path)):
            cfg_p = Path(self.config)
            if cfg_p.exists() and cfg_p.is_file():
                try:
                    return Config.parse(cfg_p)
                except Exception:
                    try:
                        with open(cfg_p, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f)
                        return Config.model_validate(data)
                    except Exception:
                        return None
        elif isinstance(self.config, dict):
            return Config.model_validate(self.config)
        return None

    def run_autograder_for_submission(
        self,
        submission_path: str | Path | list[str | Path] | tuple[str | Path, ...] | None = None,
        *,
        submission_dir: str | Path | list[str | Path] | tuple[str | Path, ...] | None = None,
        expected_score: int | float | None = None,
        save_log: bool | None = None,
        log_path: str | Path | None = None,
        verbose: bool | None = None,
    ) -> dict[str, Any]:
        actual_submission = submission_path if submission_path is not None else submission_dir

        if isinstance(actual_submission, (str, Path)):
            sub_p = Path(actual_submission)
            sub_display = sub_p.name
        elif actual_submission is not None:
            sub_display = str(actual_submission)
        else:
            sub_display = "None"

        should_save = save_log if save_log is not None else self.save_log
        resolved_log_path: Path | None = None
        cfg_dir: Path | None = None
        cfg_name: str | None = None

        if isinstance(self.config, (str, Path)):
            cfg_p = Path(self.config)
            if cfg_p.is_file() or cfg_p.suffix:
                cfg_dir = cfg_p.parent
                cfg_name = cfg_p.stem
            else:
                cfg_dir = cfg_p
                cfg_name = "config"

        clean_sub = sub_display
        if clean_sub.lower().endswith(".zip"):
            clean_sub = clean_sub[:-4]

        if log_path is not None:
            resolved_log_path = Path(log_path)
            if cfg_dir is None:
                cfg_dir = resolved_log_path.parent
                cfg_name = "config"
        elif should_save and cfg_dir is not None:
            resolved_log_path = cfg_dir / f"{cfg_name}_{clean_sub}.log"

        try:
            if self.autograder_root is not None:
                root_path = Path(self.autograder_root)
                root_path.mkdir(parents=True, exist_ok=True)
                results = self._execute(actual_submission, root_path)
            else:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    root_path = Path(tmp_dir)
                    results = self._execute(actual_submission, root_path)
        except Exception as e:
            if resolved_log_path is not None:
                try:
                    resolved_log_path.parent.mkdir(parents=True, exist_ok=True)
                    resolved_log_path.write_text(
                        f"Error executing autograder: {e}\n", encoding="utf-8"
                    )
                except Exception:
                    pass
            raise

        if isinstance(self.config, (str, Path)):
            cfg_p = Path(self.config)
            cfg_display = f"{cfg_p.parent.name}/{cfg_p.name}" if cfg_p.parent.name else cfg_p.name
        elif hasattr(self.config, "name") and self.config.name:
            cfg_display = str(self.config.name)
        else:
            cfg_display = str(self.config)

        actual_score = sum(t.get("score", 0) for t in results.get("tests", []))
        if isinstance(actual_score, float) and actual_score.is_integer():
            actual_score = int(actual_score)

        if expected_score is None and self.config_obj is not None:
            expected_score = self.config_obj.total_score

        if expected_score is not None:
            if isinstance(expected_score, float) and expected_score.is_integer():
                expected_score = int(expected_score)
            score_line = f"# Expected Score = {expected_score}, Actual Score = {actual_score}"
        else:
            score_line = f"# Actual Score = {actual_score}"

        output_buffer: list[str] = []
        header_lines = [
            f"{'#' * 80}",
            "# [AutograderRunner: Student View]",
            f"# config={cfg_display}, submission={sub_display}",
            score_line,
            f"{'#' * 80}",
        ]
        should_print = verbose if verbose is not None else self.verbose
        if should_print:
            print(f"\n{header_lines[0]}")
            for hl in header_lines[1:]:
                print(hl)
        output_buffer.extend(header_lines)

        tests = results.get("tests", [])

        def _parse_test_number(t: dict[str, Any]) -> tuple[int, ...]:
            num_str = str(t.get("number", ""))
            digits = re.findall(r"\d+", num_str)
            return tuple(int(d) for d in digits) if digits else (999999,)

        tests = sorted(tests, key=_parse_test_number)
        for t in tests:
            output = t.get("output", "").strip()
            if output:
                score = t.get("score", 0)
                if isinstance(score, float) and score.is_integer():
                    score = int(score)
                max_score = t.get("max_score", None)
                if (
                    max_score is not None
                    and isinstance(max_score, float)
                    and max_score.is_integer()
                ):
                    max_score = int(max_score)
                score_str = (
                    f"## Score: {score} / {max_score}"
                    if max_score is not None
                    else f"## Score: {score}"
                )

                output = re.sub(r"\n\n+(?:## )?Test Failed:", r"\n## Test Failed:", output)
                output = re.sub(r"(?<!## )Test Failed:", r"## Test Failed:", output)
                output = re.sub(r"(?<!## )Test Passed:", r"## Test Passed:", output)
                if "## Score: " not in output:
                    if re.search(r"(## Test (?:Passed|Failed):[^\n]*)", output):
                        output = re.sub(
                            r"(## Test (?:Passed|Failed):[^\n]*)", rf"\1\n{score_str}", output
                        )
                    else:
                        output = f"{output}\n{score_str}"

                if not output.startswith("# "):
                    number = t.get("number", "")
                    name = t.get("name", "Unknown test")
                    clean_name = re.sub(r"\s*-\s*Item\s*\d+$", "", name)
                    header = (
                        f"# {number}) {clean_name}"
                        if number and clean_name
                        else f"# {clean_name or number}"
                    )
                    section_text = f"\n{header}\n{output}"
                else:
                    section_text = f"\n{output}"

                if should_print:
                    print(section_text)
                output_buffer.append(section_text)

        if resolved_log_path is not None:
            try:
                resolved_log_path.parent.mkdir(parents=True, exist_ok=True)
                resolved_log_path.write_text(
                    "\n".join(output_buffer).strip() + "\n", encoding="utf-8"
                )
                results["log_path"] = str(resolved_log_path)
            except Exception:
                pass

        return results

    def run_autograder_for_generated_submissions(
        self,
        *,
        expected_correct_score: int | float | None = None,
        expected_wrong_score: int | float | None = 0,
        verbose: bool | None = None,
    ) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            correct_zip = td_path / "correct_answer.zip"
            correct_zip.write_bytes(self._get_correct_answer_zip_bytes())
            correct_res = self.run_autograder_for_submission(
                correct_zip, expected_score=expected_correct_score, verbose=verbose
            )

            wrong_zip = td_path / "wrong_answer.zip"
            wrong_zip.write_bytes(self._get_wrong_answer_zip_bytes())
            wrong_res = self.run_autograder_for_submission(
                wrong_zip, expected_score=expected_wrong_score, verbose=verbose
            )

        for res in (correct_res, wrong_res):
            if "log_path" in res:
                log_p = Path(res["log_path"])
                try:
                    display_path = str(log_p.resolve().relative_to(Path.cwd().resolve()))
                except ValueError:
                    display_path = str(log_p)
                print(display_path)

        return {
            "correct_answer": correct_res,
            "wrong_answer": wrong_res,
        }

    run_generated_submissions = run_autograder_for_generated_submissions

    def _prepare_source(self, source_dir: Path, gen_dir: Path) -> None:
        if self._cached_zip_bytes is not None:
            import io

            with zipfile.ZipFile(io.BytesIO(self._cached_zip_bytes), "r") as z:
                z.extractall(source_dir)
            return

        if isinstance(self.config, (str, Path)) and (
            str(self.config).endswith(".zip")
            or (Path(self.config).is_file() and zipfile.is_zipfile(self.config))
        ):
            with open(self.config, "rb") as f:
                self._cached_zip_bytes = f.read()
            with zipfile.ZipFile(self.config, "r") as z:
                z.extractall(source_dir)
            return

        generator = self._get_engine()
        output_zip = generator.generate(str(gen_dir))
        with open(output_zip, "rb") as f:
            self._cached_zip_bytes = f.read()
        correct_zip_path = Path(gen_dir) / "correct_answer.zip"
        if correct_zip_path.exists():
            with open(correct_zip_path, "rb") as f:
                self._cached_correct_zip_bytes = f.read()
        wrong_zip_path = Path(gen_dir) / "wrong_answer.zip"
        if wrong_zip_path.exists():
            with open(wrong_zip_path, "rb") as f:
                self._cached_wrong_zip_bytes = f.read()
        with zipfile.ZipFile(output_zip, "r") as z:
            z.extractall(source_dir)

    def _get_engine(self) -> Engine:
        if isinstance(self.config, (str, Path)):
            cfg_path = Path(self.config)
            if not cfg_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {cfg_path}")
            if cfg_path.is_file() and (
                str(cfg_path).endswith(".zip") or zipfile.is_zipfile(cfg_path)
            ):
                with zipfile.ZipFile(cfg_path, "r") as z:
                    if "autograder_gen.yaml" in z.namelist():
                        data = yaml.safe_load(z.read("autograder_gen.yaml"))
                        parsed_config = Config.model_validate(data)
                        return Engine(parsed_config, data)
            parsed_config = Config.parse(cfg_path)
            with open(cfg_path, "r", encoding="utf-8") as f:
                if cfg_path.suffix.lower() in [".yaml", ".yml"]:
                    original_config = yaml.safe_load(f)
                else:
                    original_config = json.load(f)
            return Engine(parsed_config, original_config)
        elif isinstance(self.config, Config):
            return Engine(self.config)
        elif isinstance(self.config, dict):
            parsed_config = Config.model_validate(self.config)
            return Engine(parsed_config, self.config)
        else:
            raise TypeError(f"Unsupported config type: {type(self.config)}")

    def _get_correct_answer_zip_bytes(self) -> bytes:
        if self._cached_correct_zip_bytes is not None:
            return self._cached_correct_zip_bytes
        if isinstance(self.config, (str, Path)):
            cfg_p = Path(self.config)
            sibling = cfg_p.parent / "correct_answer.zip"
            if sibling.is_file():
                with open(sibling, "rb") as f:
                    self._cached_correct_zip_bytes = f.read()
                return self._cached_correct_zip_bytes
        engine = self._get_engine()
        buf = engine.generate_correct_answer_zip()
        self._cached_correct_zip_bytes = buf.getvalue()
        return self._cached_correct_zip_bytes

    def _get_wrong_answer_zip_bytes(self) -> bytes:
        if self._cached_wrong_zip_bytes is not None:
            return self._cached_wrong_zip_bytes
        if isinstance(self.config, (str, Path)):
            cfg_p = Path(self.config)
            sibling = cfg_p.parent / "wrong_answer.zip"
            if sibling.is_file():
                with open(sibling, "rb") as f:
                    self._cached_wrong_zip_bytes = f.read()
                return self._cached_wrong_zip_bytes
        engine = self._get_engine()
        buf = engine.generate_wrong_answer_zip()
        self._cached_wrong_zip_bytes = buf.getvalue()
        return self._cached_wrong_zip_bytes

    def _stage_submission(
        self,
        submission_path: str | Path | list[str | Path] | tuple[str | Path, ...] | None,
        destination_dir: Path,
    ) -> None:
        if submission_path is None:
            return

        if isinstance(submission_path, (str, Path)):
            sub_p = Path(submission_path)
            if not sub_p.exists():
                return
            if sub_p.is_dir():
                for item in sub_p.iterdir():
                    dest = destination_dir / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item, dest)
            elif sub_p.is_file():
                if sub_p.suffix.lower() == ".zip" and zipfile.is_zipfile(sub_p):
                    with zipfile.ZipFile(sub_p, "r") as z:
                        z.extractall(destination_dir)
                else:
                    shutil.copy2(sub_p, destination_dir / sub_p.name)
        elif isinstance(submission_path, (list, tuple)):
            for item in submission_path:
                item_p = Path(item)
                if item_p.exists():
                    dest = destination_dir / item_p.name
                    if item_p.is_dir():
                        shutil.copytree(item_p, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(item_p, dest)

    def _execute(
        self,
        submission_path: str | Path | list[str | Path] | tuple[str | Path, ...] | None,
        root_path: Path,
    ) -> dict[str, Any]:
        source_dir = root_path / "source"
        sub_dir = root_path / "submission"
        results_dir = root_path / "results"

        source_dir.mkdir(parents=True, exist_ok=True)
        sub_dir.mkdir(parents=True, exist_ok=True)
        results_dir.mkdir(parents=True, exist_ok=True)

        gen_dir = root_path / "gen"
        self._prepare_source(source_dir, gen_dir)
        self._stage_submission(submission_path, sub_dir)

        script_path = source_dir / "run_autograder.sh"
        if not script_path.exists():
            script_path = source_dir / "run_autograder"

        if not script_path.exists():
            raise RuntimeError(f"Autograder runner script not found in {source_dir}")

        os.chmod(script_path, 0o755)

        cmd_env = {
            **os.environ,
            "AUTOGRADER_ROOT": str(root_path),
            "PYTHON": self.python_path or sys.executable,
        }
        if self.env:
            cmd_env.update(self.env)

        process = subprocess.run(
            ["bash", str(script_path)],
            cwd=str(source_dir),
            capture_output=True,
            text=True,
            timeout=self.timeout,
            env=cmd_env,
        )

        results_path = results_dir / "results.json"
        if not results_path.exists():
            error_msg = f"results.json was not created (exit code: {process.returncode})"
            if process.stderr and process.stderr.strip():
                error_msg += f"\nError output:\n{process.stderr.strip()}"
            raise RuntimeError(error_msg)

        with open(results_path, "r", encoding="utf-8") as f:
            return json.load(f)
