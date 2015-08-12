# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *

#
# This command builds lights for Unreal projects
#

class LightsCommand(Command):

    def __init__(self):
        Command.__init__(self, 'lights', 'Build lights for UE3 or UE4')


    def configure_arguments(self, env, parser):

        parser.add_argument('--context',
                            help    = 'Map context to build',
                            metavar = '<context>',
                            required = True)

        return True


    def run(self, env):
        if not hasattr(env, 'lights'):
            log_error(log_prefix() + "No light contexts specified in .nimp.conf")
            return False

        map_list = env.lights[env.context]

        if env.is_ue4:
            return ue4_lights(env, map_list)

        if env.is_ue3:
            return ue3_lights(env, map_list)

        log_error(log_prefix() + "Invalid project type {0}" % (env.project_type))
        return False

