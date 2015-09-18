# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *

#-------------------------------------------------------------------------------
class CookCommand(Command):

    def __init__(self):
        Command.__init__(self, 'cook', 'Cook contents for UE3 or UE4')

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, env, parser):
        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configurations to cook',
                            metavar = '<configuration>')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platform to cook',
                            metavar = '<platform>')

        parser.add_argument('--dlc',
                            help    = 'DLC to cook',
                            metavar = '<dlcname>',
                            default = None)

        parser.add_argument('--incremental',
                            help    = 'Perform an incremental cook',
                            action  = "store_true",
                            default = False)

        parser.add_argument('--noexpansion',
                            help    = 'Do not expand map dependencies',
                            default = False,
                            action  = "store_true")
        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        if env.is_ue4:
            return ue4_cook(env)

        if env.is_ue3:
            dlc = env.dlc if env.dlc is not None else 'main'
            maps = env.cook_maps[dlc.lower()]
            return ue3_cook(env.game,
                            maps,
                            env.languages,
                            None if env.dlc == 'main' else env.dlc,
                            env.ue3_cook_platform,
                            env.configuration,
                            env.noexpansion,
                            env.incremental)

        log_error("Invalid project type {0}", (env.project_type))
        return False

