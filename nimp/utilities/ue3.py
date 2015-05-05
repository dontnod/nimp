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

#-------------------------------------------------------------------------------
def generate_toc(env, dlc):
    for language in env.languages:
        call_process(".", [ "Binaries/CookerSync.exe",
                            env.game,
                            "-p", env.ue3_cook_platform,
                            "-x", "Loc",
                            "-r", language,
                            "-nd",
                            "-final",
                            "-dlcname", dlc])

    call_process(".", [ "Binaries/CookerSync.exe",
                        env.game,
                        "-p", env.ue3_cook_platform,
                        "-x", "ConsoleSyncProgrammer",
                        "-r", "INT",
                        "-nd",
                        "-final",
                        "-dlcname", dlc])
    return True

#---------------------------------------------------------------------------
def ue3_build(env):
    vs_version      = '11'
    solution        = env.solution
    configuration   = env.configuration
    result          = True
    version_file_cl = None

    log_verbose("Building UBT")
    if not _ue3_build_project(solution, "Development/Src/UnrealBuildTool/UnrealBuildTool.csproj", 'Release', vs_version):
        log_error("Error building UBT")
        return False

    def _build(solution, vs_version):
        if env.is_win64:
            if not _ue3_build_editor_dlls(solution, configuration, vs_version):
                return False

        if env.is_x360:
            vs_version = "10"
            solution = "whatif_vs2010.sln"

        return _ue3_build_game(solution, env.ue3_build_platform, configuration, vs_version)

    if env.generate_version_file:
        with _ue3_generate_version_file():
            return _build(solution, vs_version)
    else:
        return _build(solution, vs_version)

#---------------------------------------------------------------------------
def ue3_ship(env, destination = None):
    master_directory = env.format(env.cis_master_directory)

    if os.path.exists(master_directory):
        log_notification("Found a master at {0} : I'm going to build a patch", master_directory)
        if env.dlc == env.project:
            return _ship_game_patch(env, destination or env.cis_ship_directory)
        else:
            log_error("Sry, building a DLC patch is still not implemented")
    else:
        if env.dlc == env.project:
            log_error("Sry, building a game master is still not implemented")
        else:
            return _ship_dlc(env, destination or env.cis_ship_directory)

#---------------------------------------------------------------------------
def _ship_dlc(env, destination):
    map = env.cook_maps[env.dlc.lower()]

    log_notification("***** Cooking...")
    if not ue3_cook(env.game,
                    map,
                    env.languages,
                    env.dlc,
                    env.ue3_cook_platform,
                    'final'):
        return False

    log_notification("***** Copying DLC to output directory...")
    dlc_files = env.map_files()
    dlc_files.to(destination).load_set("DLC")

    return all_map(robocopy, dlc_files())

#---------------------------------------------------------------------------
def _ship_game_patch(env, destination):
    map = env.cook_maps[env.dlc.lower()]

    master_files = env.map_files()
    master_files_source = master_files.src(env.cis_master_directory).recursive().files()
    log_notification("***** Deploying master...")
    if not all_map(robocopy, master_files()):
        return False

    log_notification("***** Cooking on top of master...")
    if not ue3_cook(env.game,
                    map,
                    env.languages,
                    None,
                    env.ue3_cook_platform,
                    'final',
                    incremental = True):
        return False

    log_notification("***** Redeploying master cook ignoring patched files...")
    patch_files = env.map_files()
    patch_files.src(env.cis_master_directory).load_set("Patch")
    files_to_exclude = [src for src, *args in patch_files()]
    master_files_source.exclude(*files_to_exclude)
    if not all_map(robocopy, master_files()):
        return False

    if hasattr(env, 'revision'):
        cook_files = env.map_files()
        cook_files.to(env.cis_cooks_directory).load_set("Cook")
        if not all_map(robocopy, cook_files()):
            return False

    log_notification("***** Generating toc...")
    if not generate_toc(env, dlc = "Episode01" if env.dlc == env.project else env.dlc):
        return False

    if env.is_ps3:
        _generate_ps3_binaries(env)

    log_notification("***** Copying patched files to output directory...")
    patch_files = env.map_files()
    patch_files.to(destination).load_set("Patch")
    if not all_map(robocopy, patch_files()):
        return False

    if env.is_win32:
        _fix_pc_ini(env, destination)

    return True

#---------------------------------------------------------------------------
def _fix_pc_ini(env, destination):
    destination = env.format(destination)
    base_game_ini_path = os.path.join(destination, "Engine/Config/BaseGame.ini")
    os.chmod(base_game_ini_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    with open(base_game_ini_path, "r") as base_game_ini:
        ini_content = base_game_ini.read()
    with open(base_game_ini_path, "w") as base_game_ini:
        base_game_ini.write(ini_content.replace("Example", "LifeIsStrange"))

#---------------------------------------------------------------------------
def _generate_ps3_binaries(env):
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
def ue3_commandlet(game, name, args):
    game_directory = os.path.join('Binaries', 'Win64')
    game_executable = os.path.join(game + '.exe')
    game_path = os.path.join(game_directory, game_executable)
    if not os.path.exists(game_path):
        log_error('Unable to find game executable at {0}', game_path)
        return False

    cmdline = [ "./" + game_executable, name ] + args + ['-nopause', '-buildmachine', '-forcelogflush', '-unattended', '-noscriptcheck']

    return call_process(game_directory, cmdline) == 0

#---------------------------------------------------------------------------
def ue3_build_script(game):
    return ue3_commandlet(game, 'make', ['-full', '-release']) and ue3_commandlet(game, 'make', [ '-full', '-final_release' ])

#---------------------------------------------------------------------------
def ue3_cook(game, map, languages, dlc, platform, configuration, noexpansion = False, incremental = False):
    commandlet_arguments = [ map ]

    if not incremental:
        commandlet_arguments += ['-full']

    if configuration in [ 'test', 'final' ]:
        commandlet_arguments += [ '-cookforfinal' ]

    commandlet_arguments += ['-multilanguagecook=' + '+'.join(languages), '-platform='+ platform ]

    if dlc is not None:
        commandlet_arguments += ["-dlcname={0}".format(dlc)]

    if noexpansion:
        commandlet_arguments += [ '-noexpansion' ]

    return ue3_commandlet(game, 'cookpackages', commandlet_arguments)


#---------------------------------------------------------------------------
def _ue3_build_project(sln_file, project, configuration, vs_version, target = 'Rebuild'):
    base_dir = 'Development/Src'
    sln_file = os.path.join(base_dir, sln_file)

    return vsbuild(sln_file, 'Mixed platforms', configuration, project, vs_version, target)

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
    return _ue3_build_project(sln_file, platform_project, configuration, vs_version, 'Build')

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
                            'Development\Src\ExampleGame\Src\AdriftVersion.cpp',
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
