"""
Data wrangling error codes and repporting
"""

from __future__ import print_function

__author__      = "Graham Klyne (GK@ACM.ORG)"
__copyright__   = "Copyright 2013-2014, Graham Klyne"
__license__     = "MIT (http://opensource.org/licenses/MIT)"

import sys
# import os
# import os.path
# import re
# import argparse
# import errno
import logging

log = logging.getLogger(__name__)

# Exit status codes
class wrangle_errors(object):
    SUCCESS         = 0     # Success
    BADCMD          = 2     # Command error
    EXISTS          = 5     # directory already exists
    NOTEXISTS       = 6     # Directory does not exist
    MISSINGARG      = 7     # Expected argument not provided
    UNEXPECTEDARGS  = 8     # Unexpected arguments supplied
    HTTPFAIL        = 9     # HTTP error
    UNKNOWNCMD      = 11    # Unknown command name for help

def wrangle_report(status, message):
    print(message, file=sys.stderr)
    return status

def wrangle_missingarg(arglabel, options):
    return wrangle_report(
        wrangle_errors.MISSINGARG,
        "Expected %s arguments for %s not present.  Supplied arguments: (%s)"%
          (arglabel, options.command, " ".join(options.args))
        )

def wrangle_unexpected(options):
    return wrangle_report(
        wrangle_errors.UNEXPECTEDARGS,
        "Unexpected arguments for %s: (%s)"%
          (options.command, " ".join(options.args)), 
        )

# End.

