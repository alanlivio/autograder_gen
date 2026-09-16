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
    ):
        self.config_src = config_src
        self.config = config_src
        self.autograder_root = autograder_root
        self.python_path = python_path
        self.timeout = timeout
        self.env = env
        self._cached_zip_bytes: bytes | None = None

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
    ) -> dict[str, Any]:
        actual_submission = submission_path if submission_path is not None else submission_dir

        if self.autograder_root is not None:
            root_path = Path(self.autograder_root)
            root_path.mkdir(parents=True, exist_ok=True)
            results = self._execute(actual_submission, root_path)
        else:
            with tempfile.TemporaryDirectory() as tmp_dir:
                root_path = Path(tmp_dir)
                results = self._execute(actual_submission, root_path)

        if isinstance(self.config, (str, Path)):
            cfg_p = Path(self.config)
            cfg_display = f"{cfg_p.parent.name}/{cfg_p.name}" if cfg_p.parent.name else cfg_p.name
        elif hasattr(self.config, "name") and self.config.name:
            cfg_display = str(self.config.name)
        else:
            cfg_display = str(self.config)

        if isinstance(actual_submission, (str, Path)):
            sub_p = Path(actual_submission)
            sub_display = sub_p.name
        elif actual_submission is not None:
            sub_display = str(actual_submission)
        else:
            sub_display = "None"

        actual_score = sum(t.get("score", 0) for t in results.get("tests", []))
        if isinstance(actual_score, float) and actual_score.is_integer():
            actual_score = int(actual_score)

        if expected_score is None and self.config_obj is not None:
            expected_score = self.config_obj.total_score

        if expected_score is not None:
            if isinstance(expected_score, float) and expected_score.is_integer():
                expected_score = int(expected_score)
            status_str = "OK" if actual_score == expected_score else "FAIL"
            score_line = f"# Expected Score = {expected_score}, Actual Score = {actual_score}, Status = {status_str}"
        else:
            score_line = f"# Actual Score = {actual_score}"

        print(f"\n{'#' * 80}")
        print("# [AutograderRunner: Student View]")
        print(f"# config={cfg_display}, submission={sub_display}")
        print(score_line)
        print(f"{'#' * 80}")

        tests = results.get("tests", [])
        for t in tests:
            output = t.get("output", "").strip()
            if output:
                score = t.get("score", 0)
                if isinstance(score, float) and score.is_integer():
                    score = int(score)
                max_score = t.get("max_score", None)
                if max_score is not None and isinstance(max_score, float) and max_score.is_integer():
                    max_score = int(max_score)
                score_str = f"## Score: {score} / {max_score}" if max_score is not None else f"## Score: {score}"

                output = re.sub(r"\n\n+(?:## )?Test Failed:", r"\n## Test Failed:", output)
                output = re.sub(r"(?<!## )Test Failed:", r"## Test Failed:", output)
                output = re.sub(r"(?<!## )Test Passed:", r"## Test Passed:", output)
                if "## Score: " not in output:
                    if re.search(r"(## Test (?:Passed|Failed):[^\n]*)", output):
                        output = re.sub(r"(## Test (?:Passed|Failed):[^\n]*)", rf"\1\n{score_str}", output)
                    else:
                        output = f"{output}\n{score_str}"

                if not output.startswith("# "):
                    number = t.get("number", "")
                    name = t.get("name", "Unknown test")
                    clean_name = re.sub(r"\s*-\s*Item\s*\d+$", "", name)
                    header = f"# {number}) {clean_name}" if number and clean_name else f"# {clean_name or number}"
                    print(f"\n{header}\n{output}")
                else:
                    print(f"\n{output}")

        return results

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

        if isinstance(self.config, (str, Path)):
            cfg_path = Path(self.config)
            if not cfg_path.exists():
                raise FileNotFoundError(f"Configuration file not found: {cfg_path}")
            parsed_config = Config.parse(cfg_path)
            with open(cfg_path, "r", encoding="utf-8") as f:
                if cfg_path.suffix.lower() in [".yaml", ".yml"]:
                    original_config = yaml.safe_load(f)
                else:
                    original_config = json.load(f)
            generator = Engine(parsed_config, original_config)
        elif isinstance(self.config, Config):
            generator = Engine(self.config)
        elif isinstance(self.config, dict):
            parsed_config = Config.model_validate(self.config)
            generator = Engine(parsed_config, self.config)
        else:
            raise TypeError(f"Unsupported config type: {type(self.config)}")

        output_zip = generator.generate(str(gen_dir))
        with open(output_zip, "rb") as f:
            self._cached_zip_bytes = f.read()
        with zipfile.ZipFile(output_zip, "r") as z:
            z.extractall(source_dir)

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


