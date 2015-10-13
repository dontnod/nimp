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
from nimp.utilities.system import *


#---------------------------------------------------------------------------
def ue4_build(env):
    if not env.ue4_build_configuration:
        log_error("Invalid empty value for configuration")
        return False

    if env.disable_unity:
        os.environ['UBT_bUseUnityBuild'] = 'false'

    if _ue4_generate_project() != 0:
        log_error("Error generating UE4 project files")
        return False

    # The Durango XDK does not support Visual Studio 2013 yet, so if UE4
    # detected it, it created VS 2012 project files and we have to use that
    # version to build the tools instead.
    vs_version = '12'
    try:
        for line in open(env.solution):
            if '# Visual Studio 2012' in line:
                vs_version = '11'
                break
    except:
        pass

    if not hasattr(env, 'no_prerequisites') or not env.no_prerequisites:

        # For some reason nothing copies this file on OS X
        if platform.system() == 'Darwin':
            robocopy('../Engine/Binaries/ThirdParty/Ionic/Ionic.Zip.Reduced.dll',
                     '../Engine/Binaries/DotNET/Ionic.Zip.Reduced.dll')

        # Build tools from the UE4 solution if necessary
        tools = []

        if env.platform == 'win64' and env.configuration == 'devel':
            tools += [ 'DotNETUtilities',
                       'AutomationTool',
                       'UnrealFrontend',
                       'UnrealLightmass',
                       'UnrealFileServer',
                       'ShaderCompileWorker',
                       'SymbolDebugger',
                       'PS4DevKitUtil',
                       'PS4MapFileUtil',
                       'XboxOnePDBFileUtil', ]

            tools += [ 'AutomationScripts.Automation',
                       'Desktop.Automation',
                       'Linux.Automation',
                       'Mac.Automation',
                       'PS4.Automation',
                       'Win.Automation',
                       'XboxOne.Automation', ]

        if env.platform == 'ps4':
            if 'PS4MapFileUtil' not in tools: tools += [ 'PS4MapFileUtil' ]

        if env.platform == 'xboxone':
            if 'XboxOnePDBFileUtil' not in tools: tools += [ 'XboxOnePDBFileUtil' ]

        for tool in tools:
            if not _ue4_build_project(env.solution, tool,
                                      'Win64', 'Development', vs_version, 'Build'):
                log_error("Could not build %s" % (tool, ))
                return False

        # Build tools from other solutions or with other flags
        if env.platform == 'win64' and env.configuration == 'devel':

            if not _ue4_build_project(env.solution, 'BootstrapPackagedGame',
                                      'Win64', 'Shipping', vs_version, 'Build'):
                log_error("Could not build BootstrapPackagedGame")
                return False

            # This also builds AgentInterface.dll, needed by SwarmInterface.sln
            if not vsbuild('../Engine/Source/Programs/UnrealSwarm/UnrealSwarm.sln',
                           'Any CPU', 'Development', None, '11', 'Build'):
                log_error("Could not build UnrealSwarm")
                return False

            if not vsbuild('../Engine/Source/Editor/SwarmInterface/DotNET/SwarmInterface.sln',
                           'Any CPU', 'Development', None, '11', 'Build'):
                log_error("Could not build SwarmInterface")
                return False

            if not vsbuild('../Engine/Source/Programs/NetworkProfiler/NetworkProfiler.sln',
                           'Any CPU', 'Development', None, '11', 'Build'):
                log_error("Could not build NetworkProfiler")
                return False

            if not vsbuild('../Engine/Source/Programs/XboxOne/XboxOnePackageNameUtil/XboxOnePackageNameUtil.sln',
                           'x64', 'Development', None, '11', 'Build'):
                log_error("Could not build XboxOnePackageNameUtil")
                return False

    result = True
    # If we didn’t want only prerequisites, build UE4
    if not hasattr(env, 'only_prerequisites') or not env.only_prerequisites:

        # Build the main binaries
        result = _ue4_build_project(env.solution, env.game, env.ue4_build_platform,
                                    env.ue4_build_configuration, vs_version, 'Build')

    return result


#
# Generate UE4 project files
#

def _ue4_generate_project():
    if is_msys():
        return call_process('.', ['../GenerateProjectFiles.bat'])
    else:
        return call_process('..', ['/bin/sh', 'GenerateProjectFiles.sh'])


#
# Helper commands for configuration sanitising
#

def get_ue4_build_config(config, platform):
    d = { "debug"    : "Debug",
          "devel"    : "Development Editor" if platform in ["win64", "linux", "mac"] else "Development",
          "test"     : "Test",
          "shipping" : "Shipping", }
    if config not in d:
        log_warning('Unsupported UE4 build config “%s”' % (config))
        return None
    return d[config]

def get_ue4_build_platform(platform):
    d = { "ps4"     : "PS4",
          "xboxone" : "XboxOne",
          "win64"   : "Win64",
          "win32"   : "Win32",
          "linux"   : "Linux",
          "mac"     : "Mac", }
    if platform not in d:
        log_warning('Unsupported UE4 build platform “%s”' % (platform))
        return None
    return d[platform]

def get_ue4_cook_platform(platform):
    d = { "ps4"     : "FIXME",
          "xboxone" : "FIXME",
          "win64"   : "FIXME",
          "win32"   : "FIXME",
          "linux"   : "FIXME", }
    if platform not in d:
        log_warning('Unsupported UE4 cook platform “%s”' % (platform))
        return None
    return d[platform]


#---------------------------------------------------------------------------
def _ue4_build_project(sln_file, project, build_platform,
                       configuration, vs_version, target = 'Rebuild'):

    if is_msys():
        return vsbuild(sln_file, build_platform, configuration,
                       project, vs_version, target)

    elif platform.system() == 'Darwin':
        return call_process('..', ['/bin/sh', 'Engine/Build/BatchFiles/Mac/Build.sh',
                                   project, build_platform, configuration]) == 0

    else:
        project_name = project
        if configuration not in ['Development', 'Development Editor']:
            project_name += '-Linux-' + configuration
        elif configuration == 'Development Editor':
            project_name += 'Editor'
        return call_process('..', ['make', project_name]) == 0


#---------------------------------------------------------------------------
def ue4_commandlet(env, commandlet, *args):
    cmdline = [ "../Engine/Binaries/Win64/UE4Editor.exe",
                env.game,
                "-run=%s" % commandlet]

    cmdline += list(args)
    cmdline += ['-nopause', '-buildmachine', '-forcelogflush', '-unattended', '-noscriptcheck']

    return call_process(".", cmdline) == 0

