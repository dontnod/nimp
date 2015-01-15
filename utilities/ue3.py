# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
import shutil

from utilities.build        import *
from utilities.deployment   import *


VERSION_FILE_PATH = "Development\\Src\\Engine\\DNE\\DNEOnlineSuiteBuildId.h"


#---------------------------------------------------------------------------
def ue3_build(sln_file, platform, configuration, vs_version, generate_version_file = False):
    result          = True
    version_file_cl = None

    log_verbose("Building UBT")
    if not _ue3_build_project(sln_file, "UnrealBuildTool/UnrealBuildTool.csproj", 'Release', vs_version):
        log_error("Error building UBT")
        return False

    with _ue3_generate_version_file():
        if platform.lower() == 'win64':
            if not _ue3_build_editor_dlls(sln_file, configuration, vs_version):
                return False

        if not _ue3_build_game(sln_file, platform, configuration, vs_version):
            return False

    return True

#---------------------------------------------------------------------------
def ue3_commandlet(game, name, args):
    game_directory  = os.path.join('Binaries', 'Win64')
    game_path       = os.path.join(game_directory, game + '.exe')

    if not os.path.exists(game_path):
        log_error('Unable to find game executable at {0}', game_path)
        return False

    cmdline = [ game_path, name, '-nopause', '-buildmachine', '-forcelogflush' ] + args

    return call_process(game_directory, cmdline)

#---------------------------------------------------------------------------
def ue3_build_script(game):
    return ue3_commandlet(game, 'make', ['-full', '-release']) and ue3_commandlet(context, 'make', [ '-full', '-final_release' ])

#---------------------------------------------------------------------------
def ue3_cook(game, map, languages, dlc, platform, configuration, noexpansion = False):
    commandlet_arguments =  [ '-multilanguagecook=' + '+'.join(languages), '-platform='+ platform ]

    if dlc is not None:
        commandlet_arguments += ["-dlcname={0}".format(dlc)]

    if noexpansion:
        commandlet_arguments += [ '-noexpansion' ]

    if configuration in [ 'test', 'shipping' ]:
        commandlet_arguments += [ '-cookforfinal' ]

    return ue3_commandlet(game, 'cookpackages', commandlet_arguments)

#---------------------------------------------------------------------------
def _ue3_build_project(sln_file, project, configuration, vs_version, target = 'rebuild'):
    base_dir = 'Development/Src'
    project  = os.path.join(base_dir, project)
    sln_file = os.path.join(base_dir, sln_file)

    return vsbuild(sln_file, 'Mixed platforms', configuration, project, vs_version, target)

#---------------------------------------------------------------------------
def _ue3_build_editor_dlls(sln_file, configuration, vs_version):
    log_notification("Building Editor C# libraries")

    editor_config = 'Debug' if configuration.lower() == "debug" else 'Release'

    if not _ue3_build_project(sln_file, 'UnrealEdCSharp/UnrealEdCSharp.csproj', editor_config, vs_version):
        return False

    if not _ue3_build_project(sln_file, 'DNEEdCSharp/DNEEdCSharp.csproj', editor_config, vs_version):
        return False

    dll_target = os.path.join('Binaries/Win64/Editor', editor_config)
    dll_source = os.path.join('Binaries/Editor', editor_config)

    try:
        if not os.path.exists(dll_target):
            mkdir(dll_target)
        shutil.copy(os.path.join(dll_source, 'DNEEdCSharp.dll'), dll_target)
        shutil.copy(os.path.join(dll_source, 'DNEEdCSharp.pdb'), dll_target)
        shutil.copy(os.path.join(dll_source, 'UnrealEdCSharp.dll'), dll_target)
        shutil.copy(os.path.join(dll_source, 'UnrealEdCSharp.pdb'), dll_target)
    except Exception as ex:
        log_error("Error while copying editor dlls {0}".format(ex))
        return False
    return True

#-------------------------------------------------------------------------------
def _ue3_build_game(sln_file, platform, configuration, vs_version):
    dict_vcxproj = {
        'win32' :   'Windows/ExampleGame Win32.vcxproj',
        'win64' :   'Windows/ExampleGame Win64.vcxproj',
        'ps3' :     'PS3/ExampleGame PS3.vcxproj',
        'ps4' :     'ExampleGame PS4/ExampleGame PS4.vcxproj',
        'xbox360' : 'Xenon/ExampleGame Xbox360.vcxproj',
        'xboxone' : 'Dingo/ExampleGame Dingo/ExampleGame Dingo.vcxproj',
    }

    platform_project = dict_vcxproj[platform.lower()]
    return _ue3_build_project(sln_file, platform_project, configuration, vs_version, 'build')

#---------------------------------------------------------------------------
@contextlib.contextmanager
def _ue3_generate_version_file():
    version_file_format    = "#define SEE_ONLINE_SUITE_BUILD_ID \"{0}@%Y-%m-%dT%H:%M:%S.000Z@{1}-v4\"\n#define DNE_FORCE_USE_ONLINE_SUITE 1";
    machine_name           = socket.gethostname()
    random_character       = random.choice(string.ascii_lowercase)
    version_file_content   = version_file_format.format(random_character, machine_name)
    version_file_content   = time.strftime(version_file_content, time.gmtime())

    with PerforceTransaction("Version File Checkout", VERSION_FILE_PATH) as transaction:
        transaction.abort()
        write_file_content(VERSION_FILE_PATH, version_file_content)
        yield
