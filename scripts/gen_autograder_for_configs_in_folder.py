#!/usr/bin/env python3
import json
import sys
from pathlib import Path
import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import autograder_gen as ag


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
        config = ag.Config.parse(config_path)
        with open(config_path, "r", encoding="utf-8") as f:
            if config_path.suffix.lower() in [".yaml", ".yml"]:
                original_config = yaml.safe_load(f)
            else:
                original_config = json.load(f)

        engine = ag.Engine(config, original_config)
        out_dir = config_path.parent
        zip_path_str = engine.generate(str(out_dir))
        zip_path = Path(zip_path_str)
        try:
            display_path = str(zip_path.resolve().relative_to(Path.cwd().resolve()))
        except ValueError:
            display_path = str(zip_path)
        print(display_path)


if __name__ == "__main__":
    main()
