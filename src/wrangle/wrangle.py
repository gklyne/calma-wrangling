# !/usr/bin/env python
#
# wrangle.py - CALMA data wrangling
#

from __future__ import print_function

__author__      = "Graham Klyne (GK@ACM.ORG)"
__copyright__   = "Copyright 2013-2014, Graham Klyne"
__license__     = "MIT (http://opensource.org/licenses/MIT)"

import sys
import os
import os.path
import re
import argparse
import logging
import errno

log = logging.getLogger(__name__)

# if __name__ == "__main__":
dirhere = os.path.dirname(os.path.realpath(__file__))
srcroot = os.path.dirname(os.path.join(dirhere))
sys.path.insert(0, srcroot)
# sys.path.insert(0, dirhere)

from wrangle_errors import wrangle_errors, wrangle_unexpected, wrangle_report
from calma_data     import (
    explore_analysis, 
    export_analysis, export_annalist_metadata, export_annalist_subjects,
    export_analyses_multiple
    )

VERSION = "0.1.1"

command_summary_help = ("\n"+
    "Commands:\n"+
    "\n"+
    "  %(prog)s explore_analysis URL\n"+
    "  %(prog)s export_metadata URL\n"+
    "  %(prog)s export_subjects URL\n"+
    "  %(prog)s export_multiple_analyses URL\n"+
    "  %(prog)s export_all URL\n"+
    "  %(prog)s help [command]\n"+
    "  %(prog)s version\n"+
    "")

def progname(args):
    return os.path.basename(args[0])

def wrangle_version(srcroot, userhome, options):
    print(VERSION)

def wrangle_help(options, progname):
    if len(options.args) > 1:
        print("Unexpected arguments for %s: (%s)"%(options.command, " ".join(options.args)), file=sys.stderr)
        return wrangle_errors.UNEXPECTEDARGS
    status = wrangle_errors.SUCCESS
    if len(options.args) == 0:
        help_text = (
            command_summary_help+
            "\n"+
            "For more information about command options, use:\n"+
            "\n"+
            "  %(prog)s --help\n"+
            "")
    # ... 
    elif options.args[0].startswith("ver"):
        help_text = ("\n"+
            "  %(prog)s version\n"+
            "\n"+
            "Sends the software version string to standard output.\n"+
            "\n"+
            "")
    else:
        help_text = "Unrecognized command for %s: (%s)"%(options.command, options.args[0])
        status = wrangle_errors.UNKNOWNCMD
    print(help_text%{'prog': progname}, file=sys.stderr)
    return status

def parseCommandArgs(argv):
    """
    Parse command line arguments

    argv            argument list from command line

    Returns a pair consisting of options specified as returned by
    OptionParser, and any remaining unparsed arguments.
    """
    # create a parser for the command line options
    parser = argparse.ArgumentParser(
                description="CALMA data wrangling utility",
                formatter_class=argparse.RawDescriptionHelpFormatter,
                epilog=command_summary_help
                )
    parser.add_argument('--version', action='version', version='%(prog)s '+VERSION)
    # parser.add_argument("-c", "--configuration",
    #                     action='store',
    #                     dest="configuration", metavar="CONFIG",
    #                     default="personal",
    #                     #choices=['personal', 'shared', 'devel', 'runtests'],
    #                     help="Select site configuration by name (e.g. personal, shared, devel, runtests.")
    # parser.add_argument("-f", "--force",
    #                     action='store_true',
    #                     dest="force",
    #                     help="Force overwrite of existing site data.")
    parser.add_argument("--debug",
                        action="store_true", 
                        dest="debug", 
                        default=False,
                        help="Run with full debug output enabled")
    parser.add_argument("command", metavar="COMMAND",
                        nargs=None,
                        help="sub-command, one of the options listed below."
                        )
    parser.add_argument("args", metavar="ARGS",
                        nargs="*",
                        help="Additional arguments, depending on the command used."
                        )
    # parse command line now
    options = parser.parse_args(argv)
    if options:
        if options and options.command:
            return options
    print("No valid usage option given.", file=sys.stderr)
    parser.print_usage()
    return None

def run(userhome, userconfig, options, progname):
    # if options.command.startswith("runt"):                  # runtests
    #     return am_runtests(srcroot, options)
    # if options.command.startswith("init"):                  # initialize
    #     return am_initialize(srcroot, userhome, userconfig, options)
    if options.command.startswith("explore"):
        return explore_analysis(srcroot, userhome, userconfig, options)
    if options.command.startswith("export_met"):
        return export_annalist_metadata(srcroot, userhome, userconfig, options)
    if options.command.startswith("export_sub"):
        return export_annalist_subjects(srcroot, userhome, userconfig, options)
    if options.command.startswith("export_mul"):
        return export_analyses_multiple(srcroot, userhome, userconfig, options)
    if options.command.startswith("export_ana"):
        return export_analysis(srcroot, userhome, userconfig, options)
    if options.command.startswith("ver"):                   # version
        return wrangle_version(srcroot, userhome, options)
    if options.command.startswith("help"):
        return wrangle_help(options, progname)
    print("Unrecognized sub-command: %s"%(options.command), file=sys.stderr)
    print("Use '%s --help' to see usage summary"%(progname), file=sys.stderr)        
    return wrangle_errors.BADCMD

def runCommand(userhome, userconfig, argv):
    """
    Run program with supplied configuration base directory, Base directory
    from which to start looking for data, and arguments.

    This is called by main function (below), and also by test suite routines.

    Returns exit status.
    """
    options = parseCommandArgs(argv[1:])
    if options and options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    # log.debug("runCommand: configbase %s, filebase %s, argv %s"%(configbase, filebase, repr(argv)))
    # log.debug("Options: %s"%(repr(options)))
    # else:
    #     logging.basicConfig()
    if options:
        progname = os.path.basename(argv[0])
        status   = run(userhome, userconfig, options, progname)
    else:
        status = wrangle_errors.BADCMD
    return status

def runMain():
    """
    Main program transfer function for setup.py console script
    """
    userhome   = os.path.expanduser("~")
    userconfig = os.path.join(userhome, ".annalist")
    return runCommand(userhome, userconfig, sys.argv)

if __name__ == "__main__":
    """
    Program invoked from the command line.
    """
    p = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, p)
    status = runMain()
    sys.exit(status)

# End.

