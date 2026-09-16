"""
Utility functions for the TIF Autograder CLI tool.
"""

import logging
import sys
from pathlib import Path


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)

    # Prevent duplicate logs
    root_logger.propagate = False


def validate_file_path(file_path: str, description: str = "File") -> Path:
    """Validate that a file path exists and return Path object."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"{description} is not a file: {file_path}")
    return path


def validate_directory_path(dir_path: str, description: str = "Directory") -> Path:
    """Validate that a directory path exists and return Path object."""
    path = Path(dir_path)
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {dir_path}")
    if not path.is_dir():
        raise ValueError(f"{description} is not a directory: {dir_path}")
    return path


def create_directory(dir_path: str, description: str = "Directory") -> Path:
    """Create directory if it doesn't exist and return Path object."""
    path = Path(dir_path)
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception as e:
        raise ValueError(
            f"Failed to create {description.lower()}: {dir_path}. Error: {e}"
        )


def get_file_extension(file_path: str) -> str:
    """Get file extension from file path."""
    return Path(file_path).suffix.lower()


def is_supported_language_file(file_path: str, language: str) -> bool:
    """Check if file extension matches the specified language."""
    extension = get_file_extension(file_path)

    language_extensions = {"python": [".py"], "java": [".java"]}

    return extension in language_extensions.get(language.lower(), [])


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing/replacing invalid characters."""
    import re

    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", filename)
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(" .")
    # Ensure it's not empty
    return sanitized if sanitized else "unnamed"


def format_error_message(error: Exception, context: str = "") -> str:
    """Format error message with context."""
    if context:
        return f"{context}: {str(error)}"
    return str(error)


def print_success(message: str):
    """Print success message with ASCII [OK]."""
    print(f"[OK] {message}")


def print_error(message: str):
    """Print error message with ASCII [ERROR]."""
    print(f"[ERROR] {message}", file=sys.stderr)


def print_warning(message: str):
    """Print warning message with ASCII [WARNING]."""
    print(f"[WARNING] {message}")


def print_info(message: str):
    """Print info message with ASCII [INFO]."""
    print(f"[INFO] {message}")


def normalize(s: str) -> str:
    if s is None:
        return ""
    s = s.replace("\r\n", "\n")
    return "\n".join(line.rstrip() for line in s.splitlines() if line.strip())




