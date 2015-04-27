# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue4     import *

#-------------------------------------------------------------------------------
class Ue4BuildCommand(Command):

    def __init__(self):
        Command.__init__(self, 'ue4-build', 'Build UE4 executable')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configuration to build',
                            metavar = '<configuration>',
                            default = 'Development')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platform to build',
                            metavar = '<platform>',
                            default = 'Win64')

        parser.add_argument('--generate-version-file',
                            help    = 'Generates a code file containing build specific informations',
                            action  = "store_true",
                            default = False)
        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        return ue4_build(env)
