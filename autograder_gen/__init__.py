"""
AutograderGen package.
"""

from autograder_gen.version import __version__
from autograder_gen.config import Config, Question, MarkingItem, normalize_autograder_config
from autograder_gen.engine import Engine
from autograder_gen.validator import Validator

__all__ = [
    "__version__",
    "Config",
    "Question",
    "MarkingItem",
    "normalize_autograder_config",
    "Engine",
    "Validator",
]
