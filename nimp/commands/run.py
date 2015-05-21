# -*- coding: utf-8 -*-

import sys

from nimp.utilities.processes import *
from nimp.commands._command import *

#-------------------------------------------------------------------------------
class RunCommand(Command):

    def __init__(self):
        Command.__init__(self, 'run', 'Run arbitrary command')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('command',
                            help     = 'Command to run',
                            nargs    = argparse.REMAINDER,
                            metavar  = '<COMMAND> [<ARGUMENT>...]')
        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        cmdline = [] + env.command
        return call_process(".", cmdline,
                            stdout_callback = _stdout_callback,
                            stderr_callback = _stderr_callback) == 0

def _stdout_callback(line, default_log_function):
    print(line, file = sys.stdout)

def _stderr_callback(line, default_log_function):
    print(line, file = sys.stderr)

