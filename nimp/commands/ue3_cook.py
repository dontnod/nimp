# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue3 import *

#-------------------------------------------------------------------------------
class Ue3CookCommand(Command):

    def __init__(self):
        Command.__init__(self, 'ue3-cook', 'Cook contents using UE3')

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
        dlc = env.dlc if env.dlc is not None else env.project['name']
        map = env.cook['maps'][dlc.lower()]
        return ue3_cook(env.project['game_name'],
                        map,
                        env.cook['languages'],
                        None if env.project['name'] == env.dlc else env.dlc,
                        env.ue3_cook_platform,
                        env.configuration,
                        env.noexpansion,
                        env.incremental)
