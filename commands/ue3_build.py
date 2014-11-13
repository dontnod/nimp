# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time

from commands.command       import *
from commands.vsbuild       import *

from config.system          import *

from utilities.files        import *
from utilities.hashing      import *
from utilities.paths        import *
from utilities.perforce     import *
from utilities.processes    import *

VERSION_FILE_PATH = "Development\\Src\\Engine\\DNE\\DNEOnlineSuiteBuildId.h"

#-------------------------------------------------------------------------------
class Ue3BuildCommand(Command):

    def __init__(self):
        Command.__init__(self, 'ue3-build', 'Build UE3 executable')

    #---------------------------------------------------------------------------
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

        parser.add_argument('--generate-version-file',
                            help    = 'Generates a code file containing build specific informations',
                            action  = "store_true",
                            default = False)
        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        settings = context.settings
        arguments = context.arguments

        platforms               = arguments.platform
        configurations          = arguments.configuration
        result                  = True
        base_dir                = 'Development/Src'
        version_file_cl         = None

        if arguments.generate_version_file:
            version_file_cl = checkout_and_generate_version_file()

        success = True
        for builder_args in _enumerate_builder_args(base_dir, configurations, platforms):
            if not self._run_sub_command(context, VsBuildCommand(), builder_args):
                success = False
                break

        if version_file_cl is not None:
            p4_revert_changelist(version_file_cl)

        return success

#---------------------------------------------------------------------------
def checkout_and_generate_version_file():
     version_file_format    = "#define SEE_ONLINE_SUITE_BUILD_ID \"{0}@%Y-%m-%dT%H:%M:%S.000Z@{1}-v4\"\n#define DNE_FORCE_USE_ONLINE_SUITE 1";
     machine_name           = socket.gethostname()
     random_character       = random.choice(string.ascii_lowercase)
     version_file_content   = version_file_format.format(random_character, machine_name)
     version_file_content   = time.strftime(version_file_content, time.gmtime())

     cl_number = p4_edit_in_changelist("Version file checkout", VERSION_FILE_PATH)

     if cl_number is None:
         return None

     write_file_content(VERSION_FILE_PATH, version_file_content)

     return cl_number

#-------------------------------------------------------------------------------
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

