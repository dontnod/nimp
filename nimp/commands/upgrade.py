# -*- coding: utf-8 -*-

import sys

from nimp.utilities.processes import *
from nimp.commands._command import *

#-------------------------------------------------------------------------------
class UpgradeCommand(Command):

    def __init__(self):
        Command.__init__(self, 'upgrade', 'Upgrade Nimp')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        cmdline = ['pip3', 'install', '--no-index', '--upgrade', '--no-deps', 'git+http://git/nimp.git']

        return call_process(".", cmdline,
                            stdout_callback = _stdout_callback,
                            stderr_callback = _stderr_callback) == 0

def _stdout_callback(line, default_log_function):
    print(line, file = sys.stdout)

def _stderr_callback(line, default_log_function):
    print(line, file = sys.stderr)

