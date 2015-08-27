# -*- coding: utf-8 -*-

from nimp.commands._cis_command import *
from nimp.utilities.wwise import *

#-------------------------------------------------------------------------------
class BuildWwiseBanksCommand(Command):

    def __init__(self):
        Command.__init__(self, 'wwise-build-banks', 'Builds Wwise Banks')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('-p',
                            '--platform',
                            help    = 'Platform to build',
                            metavar = '<platform>')

        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        return build_wwise_banks(env)

