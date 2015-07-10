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
from nimp.utilities.perforce import *


#---------------------------------------------------------------------------
def ue4_build(env):
    vs_version = '12'

    if not env.ue4_build_configuration:
        log_error(log_prefix() + "Invalid empty value for configuration")
        return False

    if _ue4_generate_project() != 0:
        log_error(log_prefix() + "Error generating UE4 project files")
        return False

    if env.ue4_build_platform == 'PS4':
        if not _ue4_build_project(env.solution, 'PS4MapFileUtil', 'Win64',
                                  env.ue4_build_configuration, vs_version, 'Build'):
            log_error(log_prefix() + "Could not build PS4MapFileUtil.exe")
            return False

    # The Durango XDK does not support Visual Studio 2013 yet
    if env.is_xone:
        vs_version = '11'

    return _ue4_build_project(env.solution, env.game, env.ue4_build_platform,
                              env.ue4_build_configuration, vs_version, 'Build')


#---------------------------------------------------------------------------
def _ue4_generate_project():
    return call_process('.', ['../GenerateProjectFiles.bat'])

#---------------------------------------------------------------------------
def ue4_build_tools(env):
    vs_version = '12'
    tools_to_build = [tool.lower() for tool in env.tools_to_build]
    cl_name = "[CIS] Built tools from CL %s" % env.revision if hasattr(env, 'revision') else 'Build Tools'

    with p4_transaction(cl_name, submit_on_success = not env.no_checkin) as trans:
        def checkout_binaries(*globs):
            files_to_checkout = env.map_files()
            files_to_checkout.src('../Engine/Binaries').glob(*globs)
            return all_map(checkout(trans), files_to_checkout())

        def add_binaries(*globs):
            files_to_checkout = env.map_files()
            files_to_checkout.src('../Engine/Binaries').glob(*globs)
            for source, dest in files_to_checkout():
                if not trans.add(source):
                    return False
            return True

        def build_unreal_project(project, *files_to_checkout):
            if not checkout_binaries(*files_to_checkout):
                return False
            else:
                result = _ue4_build_project(env.solution, project, 'Win64', 'Development', vs_version, 'Rebuild')
                return result and add_binaries(*files_to_checkout)

        result = True

        if 'dotnetutilities' in tools_to_build:
            log_notification("Building DotNETUtilities")
            result &= build_unreal_project('DotNETUtilities', 'DotNET/DotNETUtilities.*')
        if 'lightmass' in tools_to_build:
            log_notification("Building UnrealLightMass")
            result &= build_unreal_project('UnrealLightMass', 'Win64/UnrealLightmass.*', 'Win64/UnrealLightmass-*.*')
        if 'shadercompileworker' in tools_to_build:
            log_notification("Building ShaderCompileWorker")
            result &= build_unreal_project('ShaderCompileWorker', 'Win64/ShaderCompileWorker.*', 'Win64/ShaderCompileWorker-*.*')
        if 'symboldebugger' in tools_to_build:
            log_notification("Building SymbolDebugger")
            result &= build_unreal_project('SymbolDebugger', 'Win64/SymbolDebugger.*')
        if 'unrealfileserver' in tools_to_build:
            log_notification("Building UnrealFileServer")
            result &= build_unreal_project('UnrealFileServer', 'Win64/UnrealFileServer.*')
        if 'unrealfrontend' in tools_to_build:
            log_notification("Building UnrealFrontend")
            result &= build_unreal_project('UnrealFrontend', 'Win64/UnrealFrontend.*', 'Win64/UnrealFrontend-*.*', 'Win64/PS4/UnrealFrontend-*.*')
        if 'swarm' in tools_to_build:
            log_notification("Building Swarm")
            binaries = ['DotNET/AgentInterface.*',
                        'DotNET/SwarmAgent.*',
                        'DotNET/SwarmCoordinator.*',
                        'DotNET/SwarmCoordinatorInterface.*',
                        'DotNET/UnrealControls.*',
                        'Win64/AgentInterface.*']
            if not checkout_binaries(*binaries):
                result = False
            else:
                result &= vsbuild('../Engine/Source/Programs/UnrealSwarm/UnrealSwarm.sln', 'Any CPU', 'Development', None, '10', 'Rebuild')
                result &= add_binaries(*binaries)
        if 'networkprofiler' in tools_to_build:
            log_notification("Building NetworkProfiler")
            if not checkout_binaries('DotNET/NetworkProfiler.*'):
                result = False
            else:
                result &= vsbuild('../Engine/Source/Programs/NetworkProfiler/NetworkProfiler.sln', 'Any CPU', 'Development', None, '10', 'Rebuild')
                result &= add_binaries('DotNET/NetworkProfiler.*')
        if not result:
            trans.abort()
        return result
#---------------------------------------------------------------------------
def _ue4_build_project(sln_file, project, build_platform,
                       configuration, vs_version, target = 'Rebuild'):

    return vsbuild(sln_file, build_platform, configuration,
                   project, vs_version, target)


#---------------------------------------------------------------------------
def ue4_commandlet(env, commandlet, *args):
    cmdline = [ "../Engine/Binaries/Win64/UE4Editor.exe",
                env.game,
                "-run=%s" % commandlet]

    cmdline += list(args)
    cmdline += ['-nopause', '-buildmachine', '-forcelogflush', '-unattended', '-noscriptcheck']

    return call_process(".", cmdline) == 0

