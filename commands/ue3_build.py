# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------

from commands._command import *
from utilities.ue3     import *

#-------------------------------------------------------------------------------
class Ue3BuildCommand(Command):

    def __init__(self):
        Command.__init__(self, 'ue3-build', 'Build UE3 executable')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configurations to build',
                            metavar = '<configuration>',
                            nargs   = '+',
                            default = context.default_ue3_configurations)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to build',
                            metavar = '<platform>',
                            nargs   = '+',
                            default = context.default_ue3_platforms)

        parser.add_argument('--generate-version-file',
                            help    = 'Generates a code file containing build specific informations',
                            action  = "store_true",
                            default = False)
        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        return context.call(ue3_build)
