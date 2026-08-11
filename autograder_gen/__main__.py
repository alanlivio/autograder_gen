"""
Entry point for running autograder_gen as a module: python -m autograder_gen
"""

import sys
from autograder_gen.cli import main

if __name__ == "__main__":
    sys.exit(main())
