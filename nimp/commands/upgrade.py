# -*- coding: utf-8 -*-

import sys

from nimp.utilities.processes import *
from nimp.commands._command import *

class UpgradeCommand(Command):
    def __init__(self):
        Command.__init__(self, 'upgrade', 'Upgrade Nimp [DEPRECATED]')

    def configure_arguments(self, env, parser):
        return True

    def run(self, env):
        log_error('Sorry, nimp upgrade is no longer supported. Please use:')
        log_error('pip3 install --no-index --upgrade --no-deps git+http://git/nimp.git')
        return False

