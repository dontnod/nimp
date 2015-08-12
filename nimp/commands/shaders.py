# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *

#
# This command builds shader caches for Unreal projects
#

class ShaderCommand(Command):

    def __init__(self):
        Command.__init__(self, 'shaders', 'Build shaders for UE3 or UE4')


    def configure_arguments(self, env, parser):
        parser.add_argument('-p',
                            '--platform',
                            help    = 'target shader platform [pc, ps3, ps4, x360, xboxone, linux]',
                            metavar = '<platform>')
        return True


    def run(self, env):
        if env.is_ue4:
            return ue4_shaders(env)

        if env.is_ue3:
            return ue3_shaders(env)

        log_error(log_prefix() + "Invalid project type {0}" % (env.project_type))
        return False

