"""
Batch runner for AutograderGen configurations.
Finds all config files in target directories and runs autograders against submissions.
"""

import shutil
import sys
from pathlib import Path

from autograder_gen.autograder_runner import AutograderRunner


def find_configs(target: Path) -> list[Path]:
    if target.is_file() and target.suffix.lower() in [".yaml", ".yml"]:
        return [target]
    if not target.is_dir():
        return []

    direct_configs = [target / f for f in ("config.yaml", "config.yml") if (target / f).is_file()]
    if direct_configs:
        return [direct_configs[0]]

    sub_configs: list[Path] = []
    for pattern in ("*/config.yaml", "*/config.yml"):
        sub_configs.extend(target.glob(pattern))
    return sorted(set(sub_configs))


def main():
    target_args = sys.argv[1:]
    if not target_args:
        print(f"Usage: {Path(sys.argv[0]).name} <folder_or_config_path> [...]", file=sys.stderr)
        sys.exit(1)

    all_configs: list[Path] = []
    for arg in target_args:
        target_path = Path(arg).resolve()
        configs = find_configs(target_path)
        all_configs.extend(configs)

    all_configs = sorted(set(all_configs), key=lambda p: str(p))

    for config_path in all_configs:
        runner = AutograderRunner(config_path)
        cfg_obj = runner.config_obj
        if (
            cfg_obj is not None
            and getattr(cfg_obj, "language", "").lower() == "java"
            and shutil.which("javac") is None
        ):
            print(f"[SKIPPED] {config_path}: javac is not installed")
            continue

        runner.run_autograder_for_generated_submissions()


if __name__ == "__main__":
    main()
