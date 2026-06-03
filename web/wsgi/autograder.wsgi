#!/usr/bin/python3

# This file should be at /var/www/autograder/autograder.wsgi

import sys
import logging

sys.path.append('/var/www/autograder/autograder')
from autograder.web.app import app as application
logging.basicConfig(stream=sys.stderr)
