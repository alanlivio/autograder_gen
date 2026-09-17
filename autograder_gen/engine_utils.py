import logging
import sys
from pathlib import Path


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)

    root_logger.propagate = False


def validate_file_path(file_path: str, description: str = "File") -> Path:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"{description} is not a file: {file_path}")
    return path


def validate_directory_path(dir_path: str, description: str = "Directory") -> Path:
    path = Path(dir_path)
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {dir_path}")
    if not path.is_dir():
        raise ValueError(f"{description} is not a directory: {dir_path}")
    return path


def create_directory(dir_path: str, description: str = "Directory") -> Path:
    path = Path(dir_path)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception as e:
        raise ValueError(f"Failed to create {description.lower()}: {dir_path}. Error: {e}")


def get_file_extension(file_path: str) -> str:
    return Path(file_path).suffix.lower()


def is_supported_language_file(file_path: str, language: str) -> bool:
    extension = get_file_extension(file_path)
    language_extensions = {"python": [".py"], "java": [".java"]}
    return extension in language_extensions.get(language.lower(), [])


def sanitize_filename(filename: str) -> str:
    import re

    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    sanitized = sanitized.strip(" .")
    return sanitized if sanitized else "unnamed"


def format_error_message(error: Exception, context: str = "") -> str:
    if context:
        return f"{context}: {str(error)}"
    return str(error)


def print_success(message: str):
    print(f"[OK] {message}")


def print_error(message: str):
    print(f"[ERROR] {message}", file=sys.stderr)


def print_warning(message: str):
    print(f"[WARNING] {message}")


def print_info(message: str):
    print(f"[INFO] {message}")
