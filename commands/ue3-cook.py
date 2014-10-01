# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
from commands.command       import *

from configuration.system   import *

from utilities.files        import *
from utilities.hashing      import *
from utilities.paths        import *
from utilities.processes    import *

#-------------------------------------------------------------------------------
# Ue3CookCommand
#-------------------------------------------------------------------------------
class Ue3CookCommand(Command):

    def __init__(self):
        Command.__init__(self, 'ue3-cook', 'Cook contents using UE3')

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('-g',
                            '--game',
                            metavar = '<game>',
                            type    = str,
                            default = settings.default_ue3_game)

        parser.add_argument('maps',
                            metavar = '<map>',
                            type    = str,
                            nargs   = '+')

        parser.add_argument('--noexpansion',
                            help    = 'Do not expand map dependencies',
                            default = False,
                            action  = "store_true")

        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configurations to cook',
                            metavar = '<configuration>',
                            nargs   = '+',
                            default = settings.default_ue3_configurations)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to cook',
                            metavar = '<platform>',
                            nargs   = '+',
                            default = settings.default_ue3_platforms)

        parser.add_argument('-l',
                            '--lang',
                            help    = 'languages to cook',
                            metavar = '<lang>',
                            nargs   = '+',
                            default = "INT")
        return True

    #---------------------------------------------------------------------------
    # run
    def run(self, context):
        settings = context.settings
        arguments = context.arguments

        # Import settings

        ue3_directory = settings.ue3_directory

        # Import arguments

        game = arguments.game
        maps = arguments.maps
        platforms = arguments.platform
        configurations = arguments.configuration
        noexpansion = arguments.noexpansion
        lang = arguments.lang

        # Validate environment

        cooker_dir = os.path.join(ue3_directory, 'Binaries', 'Win64')
        cooker_path = os.path.join(cooker_dir, game + '.exe')
        if not os.path.exists(cooker_path):
            log_error('Unable to find cooker in {0}', cooker_path)
            return False

        # Run task

        cmdline = [ cooker_path, 'cookpackages', '-unattended', '-nopauseonsuccess' ]
        cmdline += [ '-multilanguagecook=' + '+'.join(lang)  ]
        if noexpansion:
            cmdline += [ '-noexpansion' ]
        for cooker_args in _enumerate_cooker_args(configurations, platforms):
            if not call_process(cooker_dir, cmdline + cooker_args + maps, nimp_tag_output_filter):
                return False
        return True

#-------------------------------------------------------------------------------
# _enumerate_cooker_args
def _enumerate_cooker_args(configurations, platforms):
    for configuration in configurations:
        for platform in platforms:
            cmdline = [ '-platform=' + platform ]
            if configuration in [ 'test', 'shipping' ]:
                cmdline += [ '-cookforfinal' ]
            yield cmdline

