# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue4 import *

#-------------------------------------------------------------------------------
class Ue4CookCommand(Command):

    def __init__(self):
        Command.__init__(self, 'ue4-cook', 'Cook contents using UE4')

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
        return ue4_cook(env)
