# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue3     import *

#-------------------------------------------------------------------------------
class Ue3BuildCommand(Command):

    def __init__(self):
        Command.__init__(self, 'ue3-build', 'Build UE3 executable')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configuration to build',
                            metavar = '<configuration>',
                            default = 'release')

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
    def run(self, context):
        return ue3_build(context.solution,
                         context.platform,
                         context.configuration,
                         context.vs_version,
                         context.generate_version_file)
