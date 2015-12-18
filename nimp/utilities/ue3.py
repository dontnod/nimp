# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
import shutil
import os

from nimp.utilities.build import *
from nimp.utilities.deployment import *
from nimp.utilities.file_mapper import *
from nimp.utilities.perforce import *


#---------------------------------------------------------------------------
def ue3_build(env):
    vs_version = '11'
    solution = env.format(env.solution)
    configuration = env.ue3_build_configuration
    result = True

    if not configuration:
        log_error("Invalid empty value for configuration")
        return False

    # Shortcut for Linux builds
    if not is_msys():
        platform = env.ue3_build_platform
        return call_process(os.path.join(env.root_dir, './Development/Src'), ['make', 'all', 'CONFIGURATION=' + configuration, 'PLATFORM=' + platform, 'UBTFLAGS=-VERBOSE']) == 0

    if not _ue3_build_project(solution, "Development/Src/UnrealBuildTool/UnrealBuildTool.csproj", 'Release', vs_version):
        log_error("Error building UBT")
        return False

    # Build tools
    if env.target == 'tools':
        return _ue3_build_tools()

    def _build(solution, vs_version):
        if env.is_win64:
            if not _ue3_build_editor_dlls(solution, configuration, vs_version):
                return False

        if env.is_x360:
            vs_version = "10"
            solution = os.path.join(env.root_dir, "whatif_vs2010.sln")

        return _ue3_build_game(solution, env.ue3_build_platform, configuration, vs_version)

    # Build editor or game
    if env.target in ['game', 'editor']:
        if env.generate_version_file:
            with _ue3_generate_version_file():
                return _build(solution, vs_version)
        else:
            return _build(solution, vs_version)

    # We should not get here
    return True


#
# Rebuild shaders
#

def ue3_shaders(env):
    args = [ '-platform=' + env.ue3_shader_platform,
             '-refcache',
             '-skipmaps',
             '-allow_parallel_precompileshaders' ]
    return ue3_commandlet(env.game, 'precompileshaders', args)


#
# Rebuild lights
#

def ue3_lights(env, map_list):

    # Duplicate referent layers
    if not ue3_commandlet(env.game, 'dneduplicatereferentlayercommandlet', []):
        return False

    for map_name in map_list:

        # Build lightmaps
        if not ue3_commandlet(env.game, 'rebuildlight', [ map_name, '-quality=production', '-nocheckin' ]):
            return False

        # Build lightprobes
        if not ue3_commandlet(env.game, 'editor', [ map_name, '-buildlightprobes', '-nocheckin' ]):
            return False

    return True

#
# Helper commands for configuration sanitising
#

def get_ue3_build_config(config):
    d = { "debug"    : "Debug",
          "release"  : "Release",
          "test"     : "Test",
          "shipping" : "Shipping", }
    if config not in d:
        log_warning('Unsupported UE3 build configuration “%s”' % (config))
        return None
    return d[config]

def get_ue3_build_platform(platform):
    # Try to guess the Unreal platform name; the return
    # value should match UE3’s appGetPlatformString().
    d = { "ps4"     : "ORBIS",
          "xboxone" : "Dingo",
          "win64"   : "Win64",
          "win32"   : "Win32",
          "xbox360" : "Xbox360",
          "ps3"     : "PS3",
          "linux"   : "Linux32",
          "mac"     : "Mac", }
    if platform not in d:
        log_warning('Unsupported UE3 build platform “%s”' % (platform))
        return None
    return d[platform]

def get_ue3_cook_platform(platform):
    d = { "ps4"     : "ORBIS",
          "xboxone" : "Dingo",
          "win64"   : "PC",
          "win32"   : "PCConsole",
          "xbox360" : "Xbox360",
          "ps3"     : "PS3",
          "linux"   : "MacOSX",
          "mac"     : "MacOSX", }
    if platform not in d:
        log_warning('Unsupported UE3 cook platform “%s”' % (platform))
        return None
    return d[platform]

def get_ue3_shader_platform(platform):
    d = { "ps4"     : "ORBIS",
          "xboxone" : "Dingo",
          "win64"   : "PC",
          "win32"   : "PC",
          "xbox360" : "Xbox360",
          "ps3"     : "PS3",
          "linux"   : "Linux",
          "mac"     : "Mac", }
    if platform not in d:
        log_warning('Unsupported UE3 shader platform “%s”' % (platform))
        return None
    return d[platform]



#---------------------------------------------------------------------------
def ue3_fix_pc_ini(env, destination):
    destination = env.format(destination)
    base_game_ini_path = os.path.join(destination, "Engine/Config/BaseGame.ini")
    os.chmod(base_game_ini_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    with open(base_game_ini_path, "r") as base_game_ini:
        ini_content = base_game_ini.read()
    with open(base_game_ini_path, "w") as base_game_ini:
        base_game_ini.write(ini_content.replace("Example", "LifeIsStrange"))

#---------------------------------------------------------------------------
def ue3_generate_ps3_binaries(env):
    for config in ["Shipping", "Test"]:
        if 0 != call_process(".", ["unfself",
                                    env.format("Binaries/PS3/{game}-PS3-%s.elf" % config),
                                    env.format("Binaries/PS3/{game}-PS3-%s.elf.un" % config)]):
            return False

        if 0 != call_process(".", ["make_fself_npdrm",
                                    env.format("Binaries/PS3/{game}-PS3-%s.elf.un" % config),
                                    env.format("Binaries/PS3/EBOOT-%s.BIN" % config) ]):
            return False

#---------------------------------------------------------------------------
def ue3_commandlet(game, commandlet_name, args):

    game_directory = os.path.join('Binaries', 'Win64')
    game_binary = game + '.exe'
    game_path = os.path.join(game_directory, game_binary)
    if not os.path.exists(game_path):
        log_error("Unable to find game executable at {0}", game_path)
        return False

    args += [ '-nopause',
              '-buildmachine',
              '-forcelogflush',
              '-unattended',
              '-noscriptcheck' ]
    cmdline = [ os.path.join('.', game_binary), commandlet_name ] + args

    return call_process(game_directory, cmdline) == 0

#---------------------------------------------------------------------------
def ue3_build_script(game):
    return ue3_commandlet(game, 'make', [ '-full', '-release' ]) \
       and ue3_commandlet(game, 'make', [ '-full', '-final_release' ])

#---------------------------------------------------------------------------
def ue3_cook(game, maps, languages, dlc, platform, configuration, noexpansion = False, incremental = False):
    commandlet_arguments = maps

    if not incremental:
        commandlet_arguments += ['-full']

    if configuration in [ 'test', 'shipping' ]:
        commandlet_arguments += [ '-cookforfinal' ]

    commandlet_arguments += ['-multilanguagecook=' + '+'.join(languages), '-platform='+ platform ]

    if dlc != 'main':
        commandlet_arguments += ["-dlcname={0}".format(dlc)]

    if noexpansion:
        commandlet_arguments += [ '-noexpansion' ]

    return ue3_commandlet(game, 'cookpackages', commandlet_arguments)


#---------------------------------------------------------------------------
def _ue3_build_project(sln_file, project, configuration, vs_version):
    base_dir = 'Development/Src'
    sln_file = os.path.join(base_dir, sln_file)

    return vsbuild(sln_file, 'Mixed platforms', configuration, project, vs_version, 'Build')


#
# Build tools
#
def _ue3_build_tools():

    # We only need a 64-bit version of these ones
    win64_tools = [ 'UnrealFrontend', # needed by UnrealSwarm
                    'UnrealSwarm',
                    'MemLeakCheckDiffer',
                    'UnrealLoc',
                    'PackageDiffFrontend',
                    'StatsViewer',
                    'GameplayProfiler',
                    'MemoryProfiler2',
                    'UnSetup', ]

    # TODO 'CrashReport'? also, UnrealDVDLayout is now on ClickOnce

    # We also need a 32-bit version of these ones
    win32_64_tools = [ 'UnrealLightmass',
                       'ShaderCompileWorker', ]

    # These tools require Visual 2012
    vs2012_tools = [ 'UnrealFrontend',
                     'MemLeakCheckDiffer',
                     'UnrealLoc', ]

    # These tools require “Mixed Platforms” as the platform instead of 'x64'
    mixed_tools = [ 'UnrealFrontend' ]

    # These tools require “Any CPU”
    anycpu_tools = [ 'UnrealLoc',
                     'UnSetup',
                     'PackageDiffFrontend',
                     'StatsViewer',
                     'GameplayProfiler', ]

    for tool in win64_tools + win32_64_tools:

        override_vs_version = '10'
        override_platform = 'x64'

        if tool in vs2012_tools:
            override_vs_version = '11'

        if tool in mixed_tools:
            override_platform = 'Mixed Platforms'
        elif tool in anycpu_tools:
            override_platform = 'Any CPU'

        # Compile the x64 or Any CPU version
        if not vsbuild('Development/Tools/%s/%s.sln' % (tool, tool),
                       override_platform, 'Release', None, override_vs_version):
            log_error("Could not build %s" % (tool,))
            return False

        # If necessary, compile a Win32 version
        if tool in win32_64_tools:
            if not vsbuild('Development/Tools/%s/%s.sln' % (tool, tool),
                           'Win32', 'Release', None, override_vs_version):
                log_error("Could not build %s" % (tool,))
                return False

    # Console tools
    for tool in [ 'PS3',
                  'Windows',
                  'Xe',
                  'Dingo',
                  'Orbis', ]:

        # We need to build Win32 first then x64, at least in the case of XeTools,
        # because otherwise the project’s going to copy an incorrect version of
        # Interop.XDevkit.1.0.dll
        platforms = [ 'x64' ] if tool is 'Orbis' else [ 'Win32', 'x64' ]
        dir1 = 'Xenon' if tool is 'Xe' else tool
        dir2 = '' if tool is 'Orbis' else tool

        for platform in platforms:

            if not vsbuild('Development/Src/%s/%sTools/%sTools.sln' % (dir1, dir2, tool),
                           platform, 'Release', None, '11'):
                log_error("Could not build %sTools for %s" % (tool, platform))
                return False

    return True


#---------------------------------------------------------------------------
def _ue3_build_editor_dlls(sln_file, configuration, vs_version):
    log_notification("Building Editor C# libraries")

    editor_config = 'Debug' if configuration.lower() == "debug" else 'Release'

    if not _ue3_build_project(sln_file, 'Development/Src/UnrealEdCSharp/UnrealEdCSharp.csproj', editor_config, vs_version):
        return False

    if not _ue3_build_project(sln_file, 'Development/Src/DNEEdCSharp/DNEEdCSharp.csproj', editor_config, vs_version):
        return False

    dll_target = os.path.join('Binaries/Win64/Editor', editor_config)
    dll_source = os.path.join('Binaries/Editor', editor_config)

    try:
        safe_makedirs(dll_target)
        shutil.copy(os.path.join(dll_source, 'DNEEdCSharp.dll'), dll_target)
        shutil.copy(os.path.join(dll_source, 'DNEEdCSharp.pdb'), dll_target)
        shutil.copy(os.path.join(dll_source, 'UnrealEdCSharp.dll'), dll_target)
        shutil.copy(os.path.join(dll_source, 'UnrealEdCSharp.pdb'), dll_target)
    except Exception as ex:
        log_error("Error while copying editor dlls {0}".format(ex))
        return False
    return True

#-------------------------------------------------------------------------------
def _ue3_build_game(sln_file, ue3_build_platform, configuration, vs_version):
    dict_vcxproj = {
        'win32'   : 'Development/Src/Windows/ExampleGame Win32.vcxproj',
        'win64'   : 'Development/Src/Windows/ExampleGame Win64.vcxproj',
        'ps3'     : 'Development/Src/PS3/ExampleGame PS3.vcxproj',
        'orbis'   : 'Development/Src/ExampleGame PS4/ExampleGame PS4.vcxproj',
        'xbox360' : 'ExampleGame Xbox360', # Xbox360 Uses VS 2010
        'dingo'   : 'Development/Src/Dingo/ExampleGame Dingo/ExampleGame Dingo.vcxproj',
    }

    platform_project = dict_vcxproj[ue3_build_platform.lower()]
    return _ue3_build_project(sln_file, platform_project, configuration, vs_version)

#---------------------------------------------------------------------------
@contextlib.contextmanager
def _ue3_generate_version_file():
    with p4_transaction("Version File Checkout",
                        submit_on_success = False,
                        revert_unchanged = False) as transaction:
        _write_version_file(transaction,
                            'Development/Src/Engine/DNE/DNEOnlineSuiteBuildId.h',
                            '#define SEE_ONLINE_SUITE_BUILD_ID "{random_character}@%Y-%m-%dT%H:%M:%S.000Z@{machine_name}-v4"\n' +
                            '#define DNE_FORCE_USE_ONLINE_SUITE 1\n')
        _write_version_file(transaction,
                            'Development/Src/ExampleGame/Src/AdriftVersion.cpp',
                            '#include "ExampleGame.h"\n' +
                            '#include <AdriftVersion.h>\n' +
                            'FString fVersion = "[%Y-%m-%d_%H_%M_CL{cl}]";\n')
        yield

#---------------------------------------------------------------------------
def _write_version_file(transaction, version_file_path, version_file_format):
    transaction.add(version_file_path)
    machine_name = socket.gethostname()
    random_character = random.choice(string.ascii_lowercase)
    cl = p4_get_last_synced_changelist()
    version_file_content = version_file_format.format(random_character = random_character,
                                                      machine_name = machine_name,
                                                      cl = cl)
    version_file_content = time.strftime(version_file_content, time.gmtime())

    with open(version_file_path, "w") as version_file:
        version_file.write(version_file_content)

