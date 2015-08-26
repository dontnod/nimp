# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *

#-------------------------------------------------------------------------------
class BuildCommand(Command):

    def __init__(self):
        Command.__init__(self, 'build', 'Build UE3 or UE4 executable')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):

        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configuration to build',
                            metavar = '<configuration>')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platform to build',
                            metavar = '<platform>')

        parser.add_argument('--generate-version-file',
                            help    = 'Generates a C++ file with build information',
                            action  = "store_true",
                            default = False)

        parser.add_argument('--no-prerequisites',
                            help = 'Do not build prerequisite tools',
                            action = "store_true",
                            default = False)

        parser.add_argument('--only-prerequisites',
                            help = 'Only build prerequisite tools',
                            action = "store_true",
                            default = False)

        return True


    #---------------------------------------------------------------------------
    def run(self, env):

        # Unreal Engine 4
        if env.is_ue4:
            return ue4_build(env)

        # Unreal Engine 3
        if env.is_ue3:
            return ue3_build(env)

        # Error!
        log_error(log_prefix() + "Invalid project type {0}" % (env.project_type))
        return False

