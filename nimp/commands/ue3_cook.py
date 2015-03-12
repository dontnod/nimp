# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue3     import *

#-------------------------------------------------------------------------------
class Ue3CookCommand(Command):

    def __init__(self):
        Command.__init__(self, 'ue3-cook', 'Cook contents using UE3')

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):
        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configurations to cook',
                            metavar = '<configuration>',
                            nargs   = '+')

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
    def run(self, context):
        dlc = context.dlc if context.dlc is not None else context.project
        map = context.cook_maps[dlc.lower()]
        return ue3_cook(context.game,
                        map,
                        context.languages,
                        dlc,
                        context.platform,
                        context.configuration,
                        context.noexpansion,
                        context.incremental)
