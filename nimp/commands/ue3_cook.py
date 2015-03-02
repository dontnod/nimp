# -*- coding: utf-8 -*-

from nimp.commands._command import *

#-------------------------------------------------------------------------------
class Ue3CookCommand(Command):

    def __init__(self):
        Command.__init__(self, 'ue3-cook', 'Cook contents using UE3')

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):
        parser.add_argument('--noexpansion',
                            help    = 'Do not expand map dependencies',
                            default = False,
                            action  = "store_true")

        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configurations to cook',
                            metavar = '<configuration>',
                            nargs   = '+')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to cook',
                            metavar = '<platform>',
                            nargs   = '+')

        parser.add_argument('--dlc',
                            help    = 'DLC to cook',
                            metavar = '<dlcname>',
                            default = 'default')
        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        context.call(ue3_cook)
