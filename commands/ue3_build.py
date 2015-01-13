# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------

from commands.command       import *
from utilities.ue3          import *

#-------------------------------------------------------------------------------
class Ue3BuildCommand(Command):

    def __init__(self):
        Command.__init__(self, 'ue3-build', 'Build UE3 executable')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configurations to build',
                            metavar = '<configuration>',
                            nargs   = '+',
                            default = settings.default_ue3_configurations)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to build',
                            metavar = '<platform>',
                            nargs   = '+',
                            default = settings.default_ue3_platforms)

        parser.add_argument('--generate-version-file',
                            help    = 'Generates a code file containing build specific informations',
                            action  = "store_true",
                            default = False)
        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        settings  = context.settings
        arguments = context.arguments

        platform                = arguments.platform
        configuration           = arguments.configuration
        generate_version_file   = arguments.generate_version_file
        vs_version              = settings.vs_version
        sln_file                = settings.solution_file

        return ue3_build(sln_file, platform, configuration, vs_version, generate_version_file)