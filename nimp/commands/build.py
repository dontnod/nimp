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

        if hasattr(env, 'project_type') and env.project_type is 'UE4':
            default_config = 'development'
        elif hasattr(env, 'project_type') and env.project_type is 'UE3':
            default_config = 'release'
        else:
            default_config = 'release'

        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configuration to build',
                            metavar = '<configuration>',
                            default = default_config)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platform to build',
                            metavar = '<platform>',
                            default = 'win64')

        parser.add_argument('--generate-version-file',
                            help    = 'Generates a code file containing build specific informations',
                            action  = "store_true",
                            default = False)
        return True


    #---------------------------------------------------------------------------
    def run(self, env):

        # Unreal Engine 4
        if hasattr(env, 'project_type') and env.project_type is 'UE4':
            return ue4_build(env)

        # Unreal Engine 3
        if hasattr(env, 'project_type') and env.project_type is 'UE3':
            return ue3_build(env)

        # Error!
        log_error(log_prefix() + "Invalid project type {0}" % (env.project_type))
        return False

