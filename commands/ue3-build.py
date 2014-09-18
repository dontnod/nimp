# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
from commands.command       import *
from commands.vsbuild       import *

from configuration.system   import *

from utilities.files        import *
from utilities.hashing      import *
from utilities.paths        import *
from utilities.processes    import *

#-------------------------------------------------------------------------------
# Ue3BuildCommand
#-------------------------------------------------------------------------------
class Ue3BuildCommand(Command):

    def __init__(self):
        Command.__init__(self, 'ue3-build', 'Build UE3 executable')

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configurations to build',
                            metavar = '<configuration>',
                            nargs   = '+',
                            default = settings.default_ue3_configurations)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to build',
                            metavar = '<platform>',
                            nargs   = '+',
                            default = settings.default_ue3_platforms)
        return True

    #---------------------------------------------------------------------------
    # run
    def run(self, context):
        settings = context.settings
        arguments = context.arguments

        # Import settings

        ue3_directory = settings.ue3_directory

        # Import arguments

        platforms = arguments.platform
        configurations = arguments.configuration

        # Run task

        base_dir = ue3_directory + '/Development/Src'
        for builder_args in _enumerate_builder_args(base_dir, configurations, platforms):
            if not self._run_sub_command(context, VsBuildCommand(), builder_args):
                return False
        return True

#-------------------------------------------------------------------------------
# _enumerate_builder_args
def _enumerate_builder_args(base_dir, configurations, platforms):
    args_sln = [ base_dir + '/whatif_vs2012.sln' ]
    args_extra = [ '-V11', '-t', 'build' ]

    dict_vcxproj = {
        'win32' :   'Windows/ExampleGame Win32.vcxproj',
        'win64' :   'Windows/ExampleGame Win64.vcxproj',
        'ps3' :     'PS3/ExampleGame PS3.vcxproj',
        'ps4' :     'ExampleGame PS4/ExampleGame PS4.vcxproj',
        'xbox360' : 'Xenon/ExampleGame Xbox360.vcxproj',
        'xboxone' : 'Dingo/ExampleGame Dingo/ExampleGame Dingo.vcxproj',
    }

    for configuration in configurations:
        for platform in platforms:
            yield args_sln + [ base_dir + '/' + dict_vcxproj[platform.lower()] ] + args_extra + [ '-c', configuration, '-p', 'Mixed platforms' ]

