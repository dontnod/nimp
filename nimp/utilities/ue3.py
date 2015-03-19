# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
import shutil
import os

from nimp.utilities.build            import *
from nimp.utilities.deployment       import *

#-------------------------------------------------------------------------------
def generate_toc(context, dlc):
    for language in context.languages:
        call_process(".", [ "Binaries\CookerSync.exe",
                            context.game,
                            "-p", context.ue3_cook_platform,
                            "-x",  "Loc",
                            "-r", language,
                            "-nd",
                            "-final",
                            "-dlcname", dlc])

    call_process(".", [ "Binaries\CookerSync.exe",
                        context.game,
                        "-p", context.ue3_cook_platform,
                        "-x",  "ConsoleSyncProgrammer",
                        "-r", "INT",
                        "-nd",
                        "-final",
                        "-dlcname", dlc])
    return True

#---------------------------------------------------------------------------
def ue3_build(context):
    solution        = context.solution
    configuration   = context.configuration
    vs_version      = context.vs_version
    result          = True
    version_file_cl = None

    log_verbose("Building UBT")
    if not _ue3_build_project(solution, "Development/Src/UnrealBuildTool/UnrealBuildTool.csproj", 'Release', vs_version):
        log_error("Error building UBT")
        return False

    def _build():
        if context.is_win64:
            if not _ue3_build_editor_dlls(solution, configuration, vs_version):
                return False

        overrided_solution      = solution
        overrided_vs_version    = vs_version
        if context.is_x360:
            overrided_vs_version = "10"
            overrided_solution   = "whatif_vs2010.sln"

        if not _ue3_build_game(overrided_solution, context.ue3_build_platform, configuration, overrided_vs_version):
            return False

        return True

    if context.generate_version_file:
        with _ue3_generate_version_file():
            return _build()
    else:
        return _build()

#---------------------------------------------------------------------------
def ue3_ship(context, destination = None):
    master_directory = context.format(context.cis_master_directory)

    if os.path.exists(master_directory):
        log_notification("Found a master at {0} : I'm going to build a patch", master_directory)
        if context.dlc == context.project:
            return _ship_game_patch(context, destination or context.cis_ship_directory)
        else:
            log_error("Sry, building a DLC patch is still not implemented")
    else:
        if context.dlc == context.project:
            log_error("Sry, building a game master is still not implemented")
        else:
            return _ship_dlc(context, destination or context.cis_ship_directory)

#---------------------------------------------------------------------------
def _ship_dlc(context, destination):
    map = context.cook_maps[context.dlc.lower()]

    log_notification("***** Cooking...")
    if not ue3_cook(context.game,
                    map,
                    context.languages,
                    context.dlc,
                    context.ue3_cook_platform,
                    'final'):
        return False

    log_notification("***** Copying DLC to output directory...")
    dlc_files = context.map_files()
    dlc_files.to(destination).load_set("DLC")

    return all_map(robocopy, dlc_files())

#---------------------------------------------------------------------------
def _ship_game_patch(context, destination):
    map = context.cook_maps[context.dlc.lower()]

    master_files = context.map_files()
    master_files_source = master_files.src(context.cis_master_directory).recursive().files()
    log_notification("***** Deploying master...")
    if not all_map(robocopy, master_files()):
        return False

    log_notification("***** Cooking on top of master...")
    if not ue3_cook(context.game,
                    map,
                    context.languages,
                    None,
                    context.ue3_cook_platform,
                    'final',
                    incremental = True):
        return False

    log_notification("***** Redeploying master cook ignoring patched files...")
    patch_files = context.map_files()
    patch_files.src(context.cis_master_directory).load_set("Patch")
    files_to_exclude = [src for src, *args in patch_files()]
    master_files_source.exclude(*files_to_exclude)
    if not all_map(robocopy, master_files()):
        return False

    if hasattr(context, 'revision'):
        cook_files = context.map_files()
        cook_files.to(context.cis_cooks_directory).load_set("Cook")
        if not all_map(robocopy, cook_files()):
            return False

    log_notification("***** Generating toc...")
    if not generate_toc(context, dlc = "Episode01" if context.dlc == context.project else context.dlc):
        return False

    if context.is_ps3:
        _generate_ps3_binaries(context)

    log_notification("***** Copying patched files to output directory...")
    patch_files = context.map_files()
    patch_files.to(destination).load_set("Patch")
    if not all_map(robocopy, patch_files()):
        return False

    if context.is_win32:
        _fix_pc_ini(context, destination)

    return True

#---------------------------------------------------------------------------
def _fix_pc_ini(context, destination):
    destination = context.format(destination)
    base_game_ini_path = os.path.join(destination, "Engine/Config/BaseGame.ini")
    os.chmod(base_game_ini_path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    with open(base_game_ini_path, "r") as base_game_ini:
        ini_content = base_game_ini.read()
    with open(base_game_ini_path, "w") as base_game_ini:
        base_game_ini.write(ini_content.replace("Example", "LifeIsStrange"))

#---------------------------------------------------------------------------
def _generate_ps3_binaries(context):
    for config in ["Shipping", "Test"]:
        if 0 != call_process(".", ["unfself",
                                    context.format("Binaries\\PS3\\{game}-PS3-%s.elf" % config),
                                    context.format("Binaries\\PS3\\{game}-PS3-%s.elf.un" % config)]):
            return False

        if 0 != call_process(".", ["make_fself_npdrm",
                                    context.format("Binaries\\PS3\\{game}-PS3-%s.elf.un" % config),
                                    context.format("Binaries\\PS3\\EBOOT-%s.BIN" % config) ]):
            return False

#---------------------------------------------------------------------------
def ue3_commandlet(game, name, args):
    game_directory  = os.path.join('Binaries', 'Win64')
    game_path       = os.path.join(game_directory, game + '.exe')

    if not os.path.exists(game_path):
        log_error('Unable to find game executable at {0}', game_path)
        return False

    cmdline = [ game_path, name ] + args + ['-nopause', '-buildmachine', '-forcelogflush', '-unattended', '-noscriptcheck']

    return call_process(game_directory, cmdline) == 0

#---------------------------------------------------------------------------
def ue3_build_script(game):
    return ue3_commandlet(game, 'make', ['-full', '-release']) and ue3_commandlet(game, 'make', [ '-full', '-final_release' ])

#---------------------------------------------------------------------------
def ue3_cook(game, map, languages, dlc, platform, configuration, noexpansion = False, incremental = False):
    commandlet_arguments =  [ map]

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
        if not os.path.exists(dll_target):
            os.makedirs(dll_target)
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
                            "Development\\Src\\Engine\\DNE\\DNEOnlineSuiteBuildId.h",
                            "#define SEE_ONLINE_SUITE_BUILD_ID \"{random_character}@%Y-%m-%dT%H:%M:%S.000Z@{machine_name}-v4\"\n#define DNE_FORCE_USE_ONLINE_SUITE 1")
        _write_version_file(transaction,
                            "Development\Src\ExampleGame\Src\AdriftVersion.cpp",
                            "#include \"ExampleGame.h\"\n" +
                            "#include <AdriftVersion.h>\n" +
                            "FString fVersion = \"[%Y-%m-%d_%H_%M_CL{cl}]\";\n")
        yield

#---------------------------------------------------------------------------
def _write_version_file(transaction, version_file_path, version_file_format):
    transaction.add(version_file_path)
    machine_name           = socket.gethostname()
    random_character       = random.choice(string.ascii_lowercase)
    cl                     = p4_get_last_synced_changelist()
    version_file_content   = version_file_format.format(random_character = random_character,
                                                        machine_name     = machine_name,
                                                        cl               = cl)
    version_file_content   = time.strftime(version_file_content, time.gmtime())

    with open(version_file_path, "w") as version_file:
        version_file.write(version_file_content)
