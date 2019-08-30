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
''' Unreal Engine 4 related stuff '''

import logging
import os
import platform
import re

import nimp.build
import nimp.system
import nimp.sys.platform
import nimp.sys.process
import nimp.summary
import nimp.unreal

def build(env):
    ''' Builds an Unreal Engine Project. config and platform arguments should
        be set on environment in order to call this function. You can use
        `nimp.environment.add_arguments` and `nimp.build.add_arguments` to do
        so.'''
    if not nimp.unreal._check_for_unreal(env):
        return False

    assert hasattr(env, 'ue4_config')
    assert env.ue4_config is not None

    if env.disable_unity:
        os.environ['UBT_bUseUnityBuild'] = 'false'

    if env.fastbuild:
        os.environ['UBT_bAllowFastBuild'] = 'true'
        os.environ['UBT_bUseUnityBuild'] = 'false'

    nimp.environment.execute_hook('prebuild', env)

    # Bootstrap if necessary
    if hasattr(env, 'bootstrap') and env.bootstrap:
        # Now generate project files
        if _ue4_generate_project(env) != 0:
            logging.error("Error generating UE4 project files")
            return False

    # The main solution file
    solution = env.format('{root_dir}/UE4.sln')

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

    # Build tools that all targets require
    if not _ue4_build_common_tools(env, solution=solution, vs_version=vs_version):
        return False

    if env.target == 'tools':
        if not _ue4_build_extra_tools(env, solution=solution, vs_version=vs_version):
            return False

    if env.target == 'game':
        if not _ue4_build_game(env, solution=solution, vs_version=vs_version):
            return False

    if env.target == 'editor':
        if not _ue4_build_editor(env, solution=solution, vs_version=vs_version):
            return False

    nimp.environment.execute_hook('postbuild', env)

    return True


def _ue4_generate_project(env):

    # Check for prerequisites
    if env.ue4_minor < 22:
        has_prereq = os.path.exists(env.format('{root_dir}/Engine/Binaries/DotNET/RPCUtility.exe'))
    else:
        has_prereq = os.path.exists(env.format('{root_dir}/Engine/Build/BinaryPrerequisitesMarker.dat'))
    if not has_prereq:
        if nimp.sys.platform.is_windows():
            command = ['cmd', '/c', 'Setup.bat', '<nul']
        else:
            command = ['/bin/sh', './Setup.sh']
        if not nimp.sys.process.call(command, cwd=env.root_dir):
            return False

    # Generate project files
    if nimp.sys.platform.is_windows():
        command = ['cmd', '/c', 'GenerateProjectFiles.bat', '<nul']
        if hasattr(env, 'vs_version'):
            if env.vs_version == '14':
                command.append('-2015')
            elif env.vs_version == '15':
                command.append('-2017')
    else:
        command = ['/bin/sh', './GenerateProjectFiles.sh']

    return nimp.sys.process.call(command, cwd=env.root_dir)


def _ue4_build_project(env, sln_file, project, build_platform,
                       configuration, vs_version, target = 'Rebuild'):

    if nimp.sys.platform.is_windows():
        return nimp.build.vsbuild(sln_file, build_platform, configuration,
                                  project=project,
                                  vs_version=vs_version,
                                  target=target)

    if platform.system() == 'Darwin':
        host_platform = 'Mac'
    else:
        host_platform = 'Linux'

    # This file uses bash explicitly
    return nimp.sys.process.call(['/bin/bash', './Engine/Build/BatchFiles/%s/Build.sh' % (host_platform),
                                  project, build_platform, configuration],
                                  cwd=env.root_dir) == 0


def _ue4_build_game(env, solution, vs_version):
    if not _ue4_build_project(env, solution, env.game, env.ue4_platform,
                              env.ue4_config, vs_version, 'Build'):
        logging.error("Could not build game project")
        return False
    return True


def _ue4_build_editor(env, solution, vs_version):
    game = env.game if hasattr(env, 'game') else 'UE4'
    if env.platform in ['linux', 'mac']:
        project = game + 'Editor'
        config = env.ue4_config
    else:
        project = game
        config = env.ue4_config + ' Editor'

    if not _ue4_build_project(env, solution, project, env.ue4_platform,
                              config, vs_version, 'Build'):
        logging.error("Could not build editor project")
        return False
    return True


def _ue4_build_common_tools(env, solution, vs_version):

    for tool in _ue4_list_common_tools(env):
        if not _ue4_build_project(env, solution, tool,
                                  'Mac' if env.platform == 'mac'
                                  else 'Linux' if env.platform == 'linux'
                                  else 'Win64',
                                  'Shipping' if tool == 'CrashReportClient'
                                  else 'Development',
                                  vs_version, 'Build'):
            logging.error("Could not build %s", tool)
            return False
    return True


def _ue4_build_extra_tools(env, solution, vs_version):

    # This moved from 'Any CPU' to 'x64' in UE4.20.
    sln = env.format('{root_dir}/Engine/Source/Programs/NetworkProfiler/NetworkProfiler.sln')
    if not nimp.build.vsbuild(sln, 'Any CPU', 'Development',
                              vs_version=vs_version, target='Build') and \
       not nimp.build.vsbuild(sln, 'x64', 'Development',
                              vs_version=vs_version, target='Build'):
        logging.error("Could not build NetworkProfiler")
        return False

    if env.platform != 'win64':
        # On Windows this is part of the main .sln, but not on Linux…
        if not nimp.build.vsbuild(env.format('{root_dir}/Engine/Source/Programs/AutomationTool/AutomationTool_Mono.sln'),
                                  'Any CPU', 'Development',
                                  vs_version=vs_version,
                                  target='Build'):
            logging.error("Could not build AutomationTool")
            return False

    if env.platform != 'mac':

        # This also builds AgentInterface.dll, needed by SwarmInterface.sln
        # This used to compile on Linux but hasn't been revisited for a while
        sln1 = env.format('{root_dir}/Engine/Source/Programs/UnrealSwarm/UnrealSwarm.sln')
        sln2 = env.format('{root_dir}/Engine/Source/Programs/UnrealSwarm/SwarmAgent.sln')
        if not nimp.build.vsbuild(sln1, 'Any CPU', 'Development',
                                  vs_version=vs_version, target='Build') and \
           not nimp.build.vsbuild(sln2, 'Any CPU', 'Development',
                                  vs_version=vs_version, target='Build'):
            logging.error("Could not build UnrealSwarm")
            return False

    # These tools seem to be Windows only for now
    if env.platform == 'win64':

        if not nimp.build.vsbuild(env.format('{root_dir}/Engine/Source/Editor/SwarmInterface/DotNET/SwarmInterface.sln'),
                                  'Any CPU', 'Development',
                                  vs_version=vs_version,
                                  target='Build'):
            logging.error("Could not build SwarmInterface")
            return False

        if not _ue4_build_project(env, solution, 'BootstrapPackagedGame',
                                  'Win64', 'Shipping', vs_version, 'Build'):
            logging.error("Could not build BootstrapPackagedGame")
            return False

        tmp = env.format('{root_dir}/Engine/Source/Programs/XboxOne/XboxOnePackageNameUtil/XboxOnePackageNameUtil.sln')
        if os.path.exists(nimp.system.sanitize_path(tmp)):
            if not nimp.build.vsbuild(tmp, 'x64', 'Development',
                                      vs_version=vs_version,
                                      target='Build'):
                logging.error("Could not build XboxOnePackageNameUtil")
                return False

    return True


def _ue4_list_common_tools(env):

    # List of tools to build
    tools = [ 'UnrealHeaderTool' ]

    # Some tools are necessary even when not building tools...
    need_ps4devkitutil = False
    need_ps4mapfileutil = env.platform == 'ps4'
    need_ps4symboltool = env.platform == 'ps4'
    need_xboxonepdbfileutil = env.platform == 'xboxone'

    if env.target == 'tools':

        tools += [ 'UnrealFrontend',
                   'UnrealFileServer',
                   'ShaderCompileWorker',
                   'UnrealPak',
                   'CrashReportClient' ]

        if env.platform != 'mac':
            tools += [ 'UnrealLightmass', ] # doesn’t build (yet?)

        # No longer needed in UE 4.16
        if env.platform == 'linux' and env.ue4_minor < 16:
            tools += [ 'CrossCompilerTool', ]

        if os.path.exists(nimp.system.sanitize_path(env.format('{root_dir}/Engine/Source/Programs/DNEAssetRegistryQuery/DNEAssetRegistryQuery.Build.cs'))):
            tools += [ 'DNEAssetRegistryQuery', ]

        if env.platform == 'win64':
            tools += [ 'DotNETUtilities',
                       'AutomationTool',
                       'UnrealCEFSubProcess',
                       'SymbolDebugger' ]
            need_ps4devkitutil = True
            need_ps4mapfileutil = True
            need_ps4symboltool = True
            need_xboxonepdbfileutil = True

    # Some tools are necessary even when not building tools...
    if need_ps4devkitutil and os.path.exists(nimp.system.sanitize_path(env.format('{root_dir}/Engine/Source/Programs/PS4/PS4DevKitUtil/PS4DevKitUtil.csproj'))):
        tools += [ 'PS4DevKitUtil' ]

    if need_ps4mapfileutil and os.path.exists(nimp.system.sanitize_path(env.format('{root_dir}/Engine/Source/Programs/PS4/PS4MapFileUtil/PS4MapFileUtil.Build.cs'))):
        tools += [ 'PS4MapFileUtil' ]

    if need_ps4symboltool and os.path.exists(nimp.system.sanitize_path(env.format('{root_dir}/Engine/Source/Programs/PS4/PS4SymbolTool/PS4SymbolTool.csproj'))):
        tools += [ 'PS4SymbolTool' ]

    if need_xboxonepdbfileutil and os.path.exists(nimp.system.sanitize_path(env.format('{root_dir}/Engine/Source/Programs/XboxOne/XboxOnePDBFileUtil/XboxOnePDBFileUtil.Build.cs'))):
        tools += [ 'XboxOnePDBFileUtil' ]

    return tools

