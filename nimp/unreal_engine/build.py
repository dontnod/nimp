# -*- coding: utf-8 -*-
# Copyright © 2014—2016 Dontnod Entertainment

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''Unreal Engine 4 related stuff'''

import logging
import os
import platform
import json
from packaging import version
from pathlib import Path
import tempfile

import nimp.build
import nimp.system
import nimp.sys.platform
import nimp.sys.process
import nimp.summary
import nimp.unreal


def build(env):
    '''Builds an Unreal Engine Project. config and platform arguments should
    be set on environment in order to call this function. You can use
    `nimp.environment.add_arguments` and `nimp.build.add_arguments` to do
    so.'''
    if not nimp.unreal._check_for_unreal(env):
        return False

    assert hasattr(env, 'unreal_config')
    assert env.unreal_config is not None

    if env.disable_unity:
        os.environ['UBT_bUseUnityBuild'] = 'false'

    if env.fastbuild:
        os.environ['UBT_bAllowFastBuild'] = 'true'
        os.environ['UBT_bUseUnityBuild'] = 'false'

    # The main solution file and vs version needed
    solution = env.format('{unreal_dir}/UE{unreal_major}.sln')
    vs_version = _get_solution_vs_version(env, solution)
    env.dotnet_version = False if env.unreal_version >= 5 else '4.6'

    hook_triggers_before_unreal_generate_project = env.is_dne_legacy_ue4 or env.unreal_version >= 5

    if hook_triggers_before_unreal_generate_project:
        nimp.environment.execute_hook('prebuild', env)

    # Bootstrap if necessary
    if hasattr(env, 'bootstrap') and env.bootstrap:
        # Now generate project files
        if _unreal_generate_project(env) != 0:
            logging.error("Error generating Unreal project files")
            return False

    if not hook_triggers_before_unreal_generate_project:
        nimp.environment.execute_hook('prebuild', env)

    # Build tools that all targets require
    if not _unreal_build_common_tools(env, solution=solution, vs_version=vs_version):
        return False

    if env.target == 'tools':
        if not _unreal_build_extra_tools(env, solution=solution, vs_version=vs_version):
            return False

    if env.target == 'game':
        if not _unreal_build_game(env, solution=solution, vs_version=vs_version):
            return False

    if env.target == 'editor':
        if not _unreal_build_editor(env, solution=solution, vs_version=vs_version):
            return False

    nimp.environment.execute_hook('postbuild', env)

    return True


### UAT + UBT helpers
def _get_solution_vs_version(env, solution):
    # Decide which VS version to use
    if hasattr(env, 'vs_version') and env.vs_version:
        vs_version = env.vs_version
    else:
        # Default to VS 2015.
        vs_version = '14'
        try:
            for line in open(solution):
                if 'MinimumVisualStudioVersion = 15' in line:
                    vs_version = '15'
                    break
        except IOError:
            pass
    return vs_version


def _pre_build(env, vs_version):
    if env.is_dne_legacy_ue4:  # The project file generation requires RPCUtility very early
        if not nimp.build.vsbuild(
            env.format('{unreal_dir}/Engine/Source/Programs/RPCUtility/RPCUtility.sln'),
            'Any CPU',
            'Development',
            None,
            '15',
            'Build',
        ):
            logging.error("Could not build RPCUtility")
            return False
    # We need to build this on Linux
    if platform.system() == 'Linux':
        breakpad_dir = env.format('{unreal_dir}/Engine/Source/ThirdParty/Breakpad')
        if not os.path.exists(breakpad_dir + '/src/tools/linux/dump_syms/dump_syms'):
            if nimp.sys.process.call(['sh', 'configure'], cwd=breakpad_dir) != 0:
                logging.error("Could not configure dump_syms")
                return False
            if nimp.sys.process.call(['make', '-j4'], cwd=breakpad_dir) != 0:
                logging.error("Could not build dump_syms")
                return False
        bse_dir = env.format('{unreal_dir}/Engine/Source/Programs/BreakpadSymbolEncoder')
        if not os.path.exists(bse_dir + '/BreakpadSymbolEncoder'):
            if nimp.sys.process.call(['bash', 'BuildBreakpadSymbolEncoderLinux.sh'], cwd=bse_dir) != 0:
                logging.error("Could not build BreakpadSymbolEncoder")
                return False

    if env.is_dne_legacy_ue4:
        if platform.system() == 'Darwin':
            solution_path = '{unreal_dir}/Engine/Source/Programs/IOS/iPhonePackager/iPhonePackager.sln'
            nimp.build.vsbuild(env.format(solution_path), 'Any CPU', 'Release', '4.5', '14', 'Build')
            # HACK: nothing creates this directory on OS X
            nimp.system.safe_makedirs(env.format('{unreal_dir}/Engine/Binaries/Mac/UnrealCEFSubProcess.app'))

    missing = [  # Files that need to be copied to Engine/Binaries
        ('Win64', 'Engine/Source/ThirdParty/FBX/2016.1.1/lib/vs2015/x64/release/libfbxsdk.dll'),
        ('Win64', 'Engine/Source/ThirdParty/FBX/2018.1.1/lib/vs2015/x64/release/libfbxsdk.dll'),
        ('Win64', 'Engine/Source/ThirdParty/IntelEmbree/Embree270/Win64/lib/embree.dll'),
        ('Win64', 'Engine/Source/ThirdParty/IntelEmbree/Embree270/Win64/lib/tbb.dll'),
        ('Win64', 'Engine/Source/ThirdParty/IntelEmbree/Embree270/Win64/lib/tbbmalloc.dll'),
        ('Win64', 'Engine/Source/ThirdParty/IntelEmbree/Embree2140/Win64/lib/embree.2.14.0.dll'),
        ('Win64', 'Engine/Source/ThirdParty/IntelEmbree/Embree2140/Win64/lib/tbb.dll'),
        ('Win64', 'Engine/Source/ThirdParty/IntelEmbree/Embree2140/Win64/lib/tbbmalloc.dll'),
        ('Linux', 'Engine/Binaries/ThirdParty/OpenAL/Linux/x86_64-unknown-linux-gnu/libopenal.so.1'),
        ('Linux', 'Engine/Binaries/ThirdParty/Steamworks/Steamv139/x86_64-unknown-linux-gnu/libsteam_api.so'),
        ('Linux', 'Engine/Source/ThirdParty/Breakpad/src/tools/linux/dump_syms/dump_syms'),
        ('Linux', 'Engine/Source/Programs/BreakpadSymbolEncoder/BreakpadSymbolEncoder'),
        ('Mac', 'Engine/Source/ThirdParty/Breakpad/src/tools/mac/dump_syms/dump_syms'),
    ]

    for directory, path in missing:
        src = env.format('{unreal_dir}/{f}', f=path)
        dst = env.format('{unreal_dir}/Engine/Binaries/{d}/{f}', d=directory, f=os.path.basename(path))
        if os.path.exists(nimp.system.sanitize_path(src)):
            nimp.system.robocopy(src, dst, ignore_older=True)


def _unreal_vsversion_to_ubt(vs_version):
    if vs_version == '14' or vs_version == '2015':
        return ['-2015']
    elif vs_version == '15' or vs_version == '2017':
        return ['-2017']
    elif vs_version == '16' or vs_version == '2019':
        return ['-2019']
    else:
        return []


def _unreal_generate_project(env):
    # Check for prerequisites
    if env.is_dne_legacy_ue4:
        has_prereq = os.path.exists(env.format('{unreal_dir}/Engine/Binaries/DotNET/OneSky.dll'))
        if not has_prereq:
            # Apparently no prebuild script has created OneSky.dll, so we try to run
            # the setup script instead.
            if nimp.sys.platform.is_windows():
                command = ['cmd', '/c', 'Setup.bat', '<nul']
            else:
                command = ['/bin/sh', './Setup.sh']
            if not nimp.sys.process.call(command, cwd=env.unreal_dir):
                return False
    else:
        # We do not use GitDependencies.exe but the build scripts depend on its
        # successful run, so create this .ue4dependencies file instead.
        Path(env.format('{unreal_dir}/.ue{unreal_major}dependencies')).touch()
        logging.debug("Skipping prereq for the reboot (already done by GenerateProjectFiles)")

    # Generate project files
    if nimp.sys.platform.is_windows():
        command = ['cmd', '/c', 'GenerateProjectFiles.bat']
        if hasattr(env, 'vs_version'):
            command += _unreal_vsversion_to_ubt(env.vs_version)
        command += ['<nul']
    else:
        command = ['/bin/sh', './GenerateProjectFiles.sh']

    return nimp.build._try_excecute(command, cwd=env.unreal_dir)


def _unreal_build_tool_ubt(env, tool, vs_version=None):
    platform = env.unreal_host_platform
    configuration = _unreal_select_tool_configuration(tool)
    if not _unreal_run_ubt(env, tool, platform, configuration, vs_version=vs_version):
        logging.error('Could not build %s', tool)
        return False
    return True


def _unreal_run_ubt(env, target, build_platform, build_configuration, vs_version=None, flags=None):
    if nimp.sys.platform.is_windows():
        command = ['cmd', '/c', 'Engine\\Build\\BatchFiles\\Build.bat']
        command += _unreal_vsversion_to_ubt(vs_version)
    else:
        command = ['/bin/bash', './Engine/Build/BatchFiles/%s/Build.sh' % env.unreal_host_platform]

    command += [target, build_platform, build_configuration]

    if flags is not None:
        command += flags

    if hasattr(env, 'ubt_version') and env.ubt_version:
        command += [f'-BuildVersion={env.ubt_version}']

    ubt_verbose_flag = '-verbose'
    if (hasattr(env, 'verbose') and env.verbose) and (ubt_verbose_flag not in command):
        command.append(ubt_verbose_flag)

    return nimp.build._try_excecute(command, cwd=env.unreal_dir) == 0


def _unreal_run_uat(env, target, build_platforms, flags=None):
    if nimp.sys.platform.is_windows():
        command = ['cmd', '/c', 'Engine\\Build\\BatchFiles\\RunUAT.bat']
    else:
        command = ['/bin/bash', './RunUAT.sh']

    if build_platforms is not str:
        build_platforms = '+'.join(build_platforms)

    command += [target, '-platforms=' + build_platforms]

    if flags is not None:
        command += flags

    return nimp.build._try_excecute(command, cwd=env.unreal_dir) == 0


### Targets


def _unreal_build_game(env, solution, vs_version):
    if env.is_dne_legacy_ue4:
        return _unreal_build_project(
            env, solution, env.game, env.unreal_platform, env.unreal_config, vs_version, 'Build'
        )

    if env.platform == 'xboxone' or env.platform == 'mpx':
        if not _unreal_build_tool_ubt(env, 'XboxOnePDBFileUtil', vs_version):
            return False

    if env.platform == 'xsx':
        if not _unreal_build_tool_ubt(env, 'XboxPDBFileUtil', vs_version):
            return False

    if env.platform == 'ps5' and env.unreal_version >= 4.26:
        if not _unreal_build_ps5_common_tools(env, solution, vs_version):
            return False

    game = env.game if hasattr(env, 'game') else env.format('UE{unreal_major}')
    if not _unreal_run_ubt(
        env, game, env.unreal_platform, env.unreal_config, vs_version=vs_version, flags=['-verbose']
    ):
        logging.error("Could not build game project")
        return False

    return True


def _unreal_build_ps5_common_tools(env, solution, vs_version):
    dep = env.format('{unreal_dir}/Engine/Platforms/PS5/Source/Programs/PS5SymbolTool/PS5SymbolTool.csproj')
    configuration = 'Release' if env.unreal_full_version < version.parse('4.26.1') else 'Development'
    if not nimp.build.msbuild(dep, 'AnyCPU', configuration, vs_version=vs_version, dotnet_version=env.dotnet_version):
        logging.error("Could not build PS5SymbolTool")
        return False
    return True


def _unreal_build_editor_swarm_interface(env, solution, vs_version):
    dep = env.format('{unreal_dir}/Engine/Source/Editor/SwarmInterface/DotNET/SwarmInterface.csproj')
    if not nimp.build.msbuild(dep, 'AnyCPU', 'Development', vs_version=vs_version, dotnet_version=env.dotnet_version):
        logging.error("Could not build SwarmInterface")
        return False


def _unreal_build_editor(env, solution, vs_version):
    if not _unreal_build_swarmagent(env, vs_version):
        return False

    if env.is_dne_legacy_ue4:
        return _unreal_build_editor_legacy(env, solution, vs_version)

    # Needed before any compilation
    _unreal_build_editor_swarm_interface(env, solution, vs_version)

    # Legacy - one game compilation
    game = env.game if hasattr(env, 'game') else env.format('UE{unreal_major}')
    editors_to_build = [game]
    # for testing
    if (
        hasattr(env, 'build_multiple_editors')
        and env.build_multiple_editors is True
        and hasattr(env, 'editors_to_build')
        and env.editors_to_build is not None
    ):
        editors_to_build = env.editors_to_build
    editors_to_build = [game + 'Editor' for game in editors_to_build]

    for editor in editors_to_build:
        if not _unreal_run_ubt(env, editor, env.unreal_platform, env.unreal_config, vs_version=vs_version):
            logging.error("Could not build editor project")
            return False

    return True


def _unreal_build_common_tools(env, solution, vs_version):
    if env.is_dne_legacy_ue4:
        return _unreal_build_common_tools_legacy(env, solution, vs_version)

    if env.is_ue4:  # DotNetUtilities has been dropped in UE5
        dep = os.path.abspath(
            env.format('{unreal_dir}/Engine/Source/Programs/DotNETCommon/DotNETUtilities/DotNETUtilities.csproj')
        )
        # UE5 : use flag to perform a dotnet restore command to avoid NETSDK1004 error that happens at first build
        # The restore process only rebuilds what's not yet rebuilt so it doesn't slow down the process.
        # source : https://docs.microsoft.com/en-us/dotnet/core/tools/sdk-errors/netsdk1004
        # TODO: is it a good default flag for farm compil?
        command_flags = ['/t:Restore'] if env.unreal_version >= 5 else None
        if not nimp.build.msbuild(
            dep,
            'AnyCPU',
            'Development',
            vs_version=vs_version,
            dotnet_version=env.dotnet_version,
            additional_flags=command_flags,
        ):
            logging.error("Could not build DotNETUtilities")
            return False

    # Compile previous prebuild stuff for UE5+ here
    if env.target == 'editor' and env.unreal_version >= 5:
        dep = env.format('{unreal_dir}/Engine/Source/Programs/UnrealSwarm/SwarmAgent.sln')
        if not nimp.build.vsbuild(dep, 'AnyCPU', 'Development', vs_version=vs_version, target='Build'):
            logging.error("Could not build SwarmAgent")
            return False

        dep = env.format('{unreal_dir}/Engine/Source/Editor/SwarmInterface/DotNET/SwarmInterface.csproj')
        if not nimp.build.msbuild(
            dep, 'AnyCPU', 'Development', vs_version=vs_version, dotnet_version=env.dotnet_version
        ):
            logging.error("Could not build SwarmInterface")
            return False

    if not _unreal_build_tool_ubt(env, 'UnrealHeaderTool', vs_version):
        return False

    return True


def _unreal_build_swarmagent(env, vs_version):
    # This also builds AgentInterface.dll, needed by SwarmInterface.sln
    # This used to compile on Linux but hasn't been revisited for a while
    if env.unreal_version < 4.20:
        dep = env.format('{unreal_dir}/Engine/Source/Programs/UnrealSwarm/UnrealSwarm.sln')
    else:
        dep = env.format('{unreal_dir}/Engine/Source/Programs/UnrealSwarm/SwarmAgent.sln')
    if not nimp.build.vsbuild(dep, 'AnyCPU', 'Development', vs_version=vs_version, target='Build'):
        logging.error("Could not build SwarmAgent")
        return False

    return True


def _unreal_build_extra_tools(env, solution, vs_version):
    if env.is_dne_legacy_ue4:
        return _unreal_build_extra_tools_legacy(env, solution, vs_version)

    uat_platforms = [env.unreal_platform]
    need_ps4tools = env.platform == 'ps4'

    # also compile console tools on Win64
    if nimp.sys.platform.is_windows():
        if env.unreal_version < 5:  # We do not handle consoles yet for ue5
            uat_platforms += ['XboxOne']  # + [ 'PS4' ]
            need_ps4tools = True

    # UAT has a special target to build common tools
    if not _unreal_run_uat(env, 'BuildCommonTools', uat_platforms):
        logging.error("BuildCommonTools failed")
        return False

    # these are not built by Epic by default
    extra_tools = [
        'CrashReportClient',
        # 'LiveCodingConsole',
        'UnrealFrontend',
        'UnrealInsights',
    ]

    if env.unreal_version < 5:  # we don't wan the following in UE5
        extra_tools += [
            'UnrealFileServer',
            'UnrealCEFSubProcess',
        ]

    # MinidumpDiagnostics not in use in 4.25+ Unreal iterations
    # Not build in UE5
    if env.unreal_version <= 4.24:
        extra_tools.append('LiveCodingConsole')
        extra_tools.append('MinidumpDiagnostics')
        extra_tools.append('SymbolDebugger')

    # CrashReportClientEditor is not built by default, however this is
    # required by the Editor
    # Note: it is normally compiled by UAT BuildTarget command but we
    # don't use it yet
    if env.unreal_version >= 4.24:
        extra_tools.append('CrashReportClientEditor')

    # extra stuff needed by ue5 only
    if env.is_ue5:
        extra_tools.append('EpicWebHelper')

    # build projects are currently broken for PS4SymbolTool
    # and BuildCommonTools.Automation.cs (4.22)
    if need_ps4tools:
        # extra_tools.append('PS4MapFileUtil') # removed in 4.22
        _unreal_build_ps4_tools_workaround(env, solution, vs_version)

    # use UBT for remaining extra tool targets
    for tool in extra_tools:
        if not _unreal_build_tool_ubt(env, tool, vs_version):
            return False

    # Build DNEAssetRegistry
    _unreal_build_DNEAssetRegistry(env, solution, vs_version)

    # Build CSVTools
    csv_tools_sln = env.format('{unreal_dir}/Engine/Source/Programs/CSVTools/CSVTools.sln')
    if not nimp.build.vsbuild(
        nimp.system.sanitize_path(csv_tools_sln), 'Any CPU', "Release", vs_version=vs_version, target='Build'
    ):
        logging.error("Could not build CSVTools")
        return False

    return True


def _unreal_build_ps4_tools_workaround(env, solution, vs_version):
    csproj = env.format('{unreal_dir}/Engine/Platforms/PS4/Source/Programs/PS4DevKitUtil/PS4DevKitUtil.csproj')
    if env.unreal_version < 4.24:
        csproj = env.format('{unreal_dir}/Engine/Source/Programs/PS4/PS4DevKitUtil/PS4DevKitUtil.csproj')
    if not nimp.build.msbuild(
        csproj, 'AnyCPU', 'Development', vs_version=vs_version, dotnet_version=env.dotnet_version
    ):
        logging.error("Could not build PS4DevKitUtil")
        return False

    csproj = env.format('{unreal_dir}/Engine/Platforms/PS4/Source/Programs/PS4SymbolTool/PS4SymbolTool.csproj')
    if env.unreal_version < 4.24:
        csproj = env.format('{unreal_dir}/Engine/Source/Programs/PS4/PS4SymbolTool/PS4SymbolTool.csproj')
    if not nimp.build.msbuild(csproj, None, None, vs_version=vs_version, dotnet_version=env.dotnet_version):
        logging.error("Could not build PS4SymbolTool")
        return False

    return True


def _unreal_select_tool_configuration(tool):
    # CrashReportClient is not built in Shipping by default,
    # however this is required by the staging process
    need_shipping = [
        'CrashReportClient',
        'CrashReportClientEditor',
        'UnrealCEFSubProcess',
        'EpicWebHelper',
    ]
    if tool in need_shipping:
        return 'Shipping'
    return 'Development'


### LEGACY (now using UAT+UBT since 4.22/reboot)


def _unreal_build_project(env, sln_file, project, build_platform, configuration, vs_version, target='Rebuild'):
    if nimp.sys.platform.is_windows():
        if nimp.build.vsbuild(
            sln_file, build_platform, configuration, project=project, vs_version=vs_version, target=target
        ):
            return True
    else:
        # This file needs bash explicitly
        if (
            nimp.sys.process.call(
                [
                    '/bin/bash',
                    './Engine/Build/BatchFiles/%s/Build.sh' % (env.unreal_host_platform),
                    project,
                    build_platform,
                    configuration,
                ],
                cwd=env.unreal_dir,
            )
            == 0
        ):
            return True
    logging.error('Could not build %s', project)
    return False


def _unreal_build_editor_legacy(env, solution, vs_version):
    game = env.game if hasattr(env, 'game') else env.format('UE{unreal_major}')
    if env.platform in ['linux', 'mac']:
        project = game + 'Editor'
        config = env.unreal_config
    else:
        project = game
        config = env.unreal_config + ' Editor'

    return _unreal_build_project(env, solution, project, env.unreal_platform, config, vs_version, 'Build')


def _unreal_build_common_tools_legacy(env, solution, vs_version):
    for tool in _unreal_list_common_tools_legacy(env):
        if not _unreal_build_project(
            env, solution, tool, env.unreal_host_platform, _unreal_select_tool_configuration(tool), vs_version, 'Build'
        ):
            return False
    return True


def _unreal_build_extra_tools_legacy(env, solution, vs_version):
    # This moved from 'AnyCPU' to 'x64' in UE4.20.
    sln = env.format('{unreal_dir}/Engine/Source/Programs/NetworkProfiler/NetworkProfiler.sln')
    if not nimp.build.vsbuild(
        sln, 'Any CPU', 'Development', vs_version=vs_version, target='Build'
    ) and not nimp.build.vsbuild(sln, 'x64', 'Development', vs_version=vs_version, target='Build'):
        logging.error("Could not build NetworkProfiler")
        return False

    if env.platform != 'win64':
        # On Windows this is part of the main .sln, but not on Linux…
        if not nimp.build.vsbuild(
            env.format('{unreal_dir}/Engine/Source/Programs/AutomationTool/AutomationTool_Mono.sln'),
            'Any CPU',
            'Development',
            vs_version=vs_version,
            target='Build',
        ):
            logging.error("Could not build AutomationTool")
            return False

    if env.platform != 'mac':
        if not _unreal_build_swarmagent(env, vs_version):
            return False

    # These tools seem to be Windows only for now
    if env.platform == 'win64':
        if not nimp.build.vsbuild(
            env.format('{unreal_dir}/Engine/Source/Editor/SwarmInterface/DotNET/SwarmInterface.sln'),
            'Any CPU',
            'Development',
            vs_version=vs_version,
            target='Build',
        ):
            logging.error("Could not build SwarmInterface")
            return False

        if not _unreal_build_project(env, solution, 'BootstrapPackagedGame', 'Win64', 'Shipping', vs_version, 'Build'):
            return False

        tmp = env.format(
            '{unreal_dir}/Engine/Source/Programs/XboxOne/XboxOnePackageNameUtil/XboxOnePackageNameUtil.sln'
        )
        if os.path.exists(nimp.system.sanitize_path(tmp)):
            if not nimp.build.vsbuild(tmp, 'x64', 'Development', vs_version=vs_version, target='Build'):
                logging.error("Could not build XboxOnePackageNameUtil")
                return False

    return True


def _unreal_list_common_tools_legacy(env):
    # List of tools to build
    tools = ['UnrealHeaderTool']

    # Some tools are necessary even when not building tools...
    need_ps4devkitutil = False
    need_ps4mapfileutil = env.platform == 'ps4'
    need_ps4symboltool = env.platform == 'ps4'
    need_xboxonepdbfileutil = env.platform == 'xboxone'

    if env.target == 'tools':
        tools += ['UnrealFrontend', 'UnrealFileServer', 'ShaderCompileWorker', 'UnrealPak', 'CrashReportClient']

        if env.platform != 'mac':
            tools += [
                'UnrealLightmass',
            ]  # doesn’t build (yet?)

        # No longer needed in UE 4.16
        if env.platform == 'linux' and env.unreal_version < 4.16:
            tools += [
                'CrossCompilerTool',
            ]

        if os.path.exists(
            nimp.system.sanitize_path(
                env.format('{unreal_dir}/Engine/Source/Programs/DNEAssetRegistryQuery/DNEAssetRegistryQuery.Build.cs')
            )
        ):
            tools += [
                'DNEAssetRegistryQuery',
            ]

        if env.platform == 'win64':
            tools += ['DotNETUtilities', 'AutomationTool', 'UnrealCEFSubProcess', 'SymbolDebugger']
            need_ps4devkitutil = True
            need_ps4mapfileutil = True
            need_ps4symboltool = True
            need_xboxonepdbfileutil = True

    # Some tools are necessary even when not building tools...
    if need_ps4devkitutil and os.path.exists(
        nimp.system.sanitize_path(
            env.format('{unreal_dir}/Engine/Source/Programs/PS4/PS4DevKitUtil/PS4DevKitUtil.csproj')
        )
    ):
        tools += ['PS4DevKitUtil']

    if need_ps4mapfileutil and os.path.exists(
        nimp.system.sanitize_path(
            env.format('{unreal_dir}/Engine/Source/Programs/PS4/PS4MapFileUtil/PS4MapFileUtil.Build.cs')
        )
    ):
        tools += ['PS4MapFileUtil']

    if need_ps4symboltool and os.path.exists(
        nimp.system.sanitize_path(
            env.format('{unreal_dir}/Engine/Source/Programs/PS4/PS4SymbolTool/PS4SymbolTool.csproj')
        )
    ):
        tools += ['PS4SymbolTool']

    if need_xboxonepdbfileutil and os.path.exists(
        nimp.system.sanitize_path(
            env.format('{unreal_dir}/Engine/Source/Programs/XboxOne/XboxOnePDBFileUtil/XboxOnePDBFileUtil.Build.cs')
        )
    ):
        tools += ['XboxOnePDBFileUtil']

    return tools


def _unreal_build_DNEAssetRegistry(env, solution, vs_version):
    '''Build DNEAssetRegistry DNE specific plugin code'''
    csproj = '{root_dir}/DNE/Source/Programs/DNEAssetRegistryQueryUpdater/DNEAssetRegistryQueryUpdater.csproj'
    dne_tool_path = '{root_dir}/DNE/Source/Programs/DNEAssetRegistryQuery/DNEAssetRegistryQuery.Build.cs'
    csproj = nimp.system.sanitize_path(env.format(csproj))
    dne_tool_path = nimp.system.sanitize_path(env.format(dne_tool_path))

    can_build = os.path.exists(csproj) and os.path.exists(dne_tool_path)

    if can_build:
        # DNEAssetRegistryQueryUpdater.exe is required by DNEAssetRegistryQuery and must be compiled first
        if not nimp.build.msbuild(
            csproj, 'AnyCPU', 'Development', vs_version=vs_version, dotnet_version=env.dotnet_version
        ):
            logging.error("Could not build DNEAssetRegistryQueryUpdater")
            return False
        if not _unreal_build_tool_ubt(env, 'DNEAssetRegistryQuery', vs_version):
            logging.error("Could not build DNEAssetRegistryQuery")
            return False


def _unreal_list_plugins_enabled(env, project=None, platform=None, config=None):
    if project is None:
        project = env.project
    if platform is None:
        platform = env.platform
    if config is None:
        config = env.config

    with tempfile.TemporaryDirectory(prefix='UBT_Plugins_export') as tmp_dir_path:
        output_file_path = Path(tmp_dir_path) / f"{project}.json"

        # Generate JSON file to know which modules are used in the project
        # -ListPlugins is a custom argument we added through a patch to UBT.
        # It add the list of the enabled plugins with the path to their directory at the end of the output file
        if not _unreal_run_ubt(
            env,
            project,
            platform,
            config,
            None,
            ['-Mode=JsonExport', '-ListPlugins', f'-OutputFile={output_file_path}'],
        ):
            raise RuntimeError("Could not run UBT to provide JSON file")

        # If the file does not exist where we think it exists, then catch error
        if not output_file_path.is_file():
            raise FileNotFoundError("JSON file does not exist")
        # Parse JSON file to get the modules
        with open(output_file_path) as f:
            data = json.load(f)

        return set(data['Plugins'].values())
