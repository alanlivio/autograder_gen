"""
Batch generator for AutograderGen configurations.
Finds all config files in target directories and generates Gradescope autograders.
"""

import json
import sys
from pathlib import Path
import yaml

from autograder_gen.config import Config
from autograder_gen.engine import Engine


def find_configs(target: Path) -> list[Path]:
    if target.is_file() and target.suffix.lower() in [".yaml", ".yml"]:
        return [target]
    if not target.is_dir():
        return []

    direct_configs = [
        target / f for f in ("config.yaml", "config.yml") if (target / f).is_file()
    ]
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
        config = Config.parse(config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix.lower() in [".yaml", ".yml"]:
                original_config = yaml.safe_load(f)
            else:
                original_config = json.load(f)

        engine = Engine(config, original_config)
        out_dir = config_path.parent
        engine.generate(str(out_dir))
        generated_assets = [
            out_dir / "autograder.zip",
            out_dir / "correct_answer.zip",
            out_dir / "wrong_answer.zip",
            out_dir / "description.docx",
            out_dir / "description.md",
            out_dir / "rubric.csv",
        ]
        for asset in generated_assets:
            if asset.exists():
                try:
                    display_path = str(asset.resolve().relative_to(Path.cwd().resolve()))
                except ValueError:
                    display_path = str(asset)
                print(display_path)


if __name__ == "__main__":
    main()
