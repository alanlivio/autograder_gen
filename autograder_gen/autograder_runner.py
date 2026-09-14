from __future__ import annotations

import json
import os
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
        config: str | Path | Config | dict[str, Any],
        *,
        autograder_root: str | Path | None = None,
        python_path: str | None = None,
        timeout: int | float | None = None,
        env: dict[str, str] | None = None,
    ):
        self.config = config
        self.autograder_root = autograder_root
        self.python_path = python_path
        self.timeout = timeout
        self.env = env
        self._cached_zip_bytes: bytes | None = None

    def run_autograder_for_submission(
        self,
        submission_path: str | Path | list[str | Path] | tuple[str | Path, ...] | None = None,
        *,
        submission_dir: str | Path | list[str | Path] | tuple[str | Path, ...] | None = None,
    ) -> dict[str, Any]:
        actual_submission = submission_path if submission_path is not None else submission_dir

        if self.autograder_root is not None:
            root_path = Path(self.autograder_root)
            root_path.mkdir(parents=True, exist_ok=True)
            return self._execute(actual_submission, root_path)

        with tempfile.TemporaryDirectory() as tmp_dir:
            root_path = Path(tmp_dir)
            return self._execute(actual_submission, root_path)

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


