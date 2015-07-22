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
def ue4_build(env):
    vs_version = '12'

    if not env.ue4_build_configuration:
        log_error(log_prefix() + "Invalid empty value for configuration")
        return False

    if _ue4_generate_project() != 0:
        log_error(log_prefix() + "Error generating UE4 project files")
        return False

    # Build tools from the UE4 solution if necessary
    tools = []

    if env.platform == 'win64' and env.configuration == 'devel':
        tools += [ 'DotNETUtilities',
                   'AutomationTool',
                   'UnrealFrontend',
                   'UnrealLightmass',
                   'UnrealFileServer',
                   'ShaderCompileWorker',
                   'SymbolDebugger', ]

    if env.platform == 'ps4':
        tools += [ 'PS4MapFileUtil' ]

    if env.platform == 'xboxone':
        tools += [ 'XboxOnePDBFileUtil' ]

    for tool in tools:
        if not _ue4_build_project(env.solution, tool, 'Win64',
                                  env.ue4_build_configuration, vs_version, 'Build'):
            log_error(log_prefix() + "Could not build %s" % (tool, ))
            return False

    # Build tools from other solutions
    if env.platform == 'win64' and env.configuration == 'devel':

        if not vsbuild('../Engine/Source/Programs/UnrealSwarm/UnrealSwarm.sln', 'Any CPU',
                       'Development', None, '10', 'Rebuild'):
            log_error(log_prefix() + "Could not build UnrealSwarm")
            return False

        if not vsbuild('../Engine/Source/Programs/NetworkProfiler/NetworkProfiler.sln', 'Any CPU',
                       'Development', None, '10', 'Rebuild'):
            log_error(log_prefix() + "Could not build NetworkProfiler")
            return False

    # The Durango XDK does not support Visual Studio 2013 yet
    if env.is_xone:
        vs_version = '11'

    # Build the main binaries
    result = _ue4_build_project(env.solution, env.game, env.ue4_build_platform,
                                env.ue4_build_configuration, vs_version, 'Build')

    return result


#
# Generate UE4 project files
#

def _ue4_generate_project():
    return call_process('.', ['../GenerateProjectFiles.bat'])


#
# Helper commands for configuration sanitising
#

def get_ue4_build_config(config, platform):
    d = { "debug"    : "Debug",
          "devel"    : "Development Editor" if platform is "win64" else "Development",
          "test"     : "Test",
          "shipping" : "Shipping", }
    if config not in d:
        log_warning(log_prefix() + 'Unsupported UE4 build config “%s”' % (config))
        return None
    return d[config]

def get_ue4_build_platform(platform):
    d = { "ps4"     : "PS4",
          "xboxone" : "XboxOne",
          "win64"   : "Win64",
          "win32"   : "Win32",
          "linux"   : "Linux", }
    if platform not in d:
        log_warning(log_prefix() + 'Unsupported UE4 build platform “%s”' % (platform))
        return None
    return d[platform]

def get_ue4_cook_platform(platform):
    d = { "ps4"     : "FIXME",
          "xboxone" : "FIXME",
          "win64"   : "FIXME",
          "win32"   : "FIXME",
          "linux"   : "FIXME", }
    if platform not in d:
        log_warning(log_prefix() + 'Unsupported UE4 cook platform “%s”' % (platform))
        return None
    return d[platform]


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

