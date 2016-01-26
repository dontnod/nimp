# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
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

    if env.fastbuild:
        os.environ['UBT_bAllowFastBuild'] = 'true'
        # FIXME: it should not be our job to set this
        os.environ['UBT_bUseUnityBuild'] = 'false'

    # The project file generation requires RPCUtility and Ionic.Zip.Reduced very early
    if not vsbuild(env.format('{root_dir}/Engine/Source/Programs/RPCUtility/RPCUtility.sln'),
                   'Any CPU', 'Development', None, '11', 'Build'):
        log_error("Could not build RPCUtility")
        return False

    # HACK: For some reason nothing copies this file on OS X
    if platform.system() == 'Darwin':
        robocopy(env.format('{root_dir}/Engine/Binaries/ThirdParty/Ionic/Ionic.Zip.Reduced.dll'),
                 env.format('{root_dir}/Engine/Binaries/DotNET/Ionic.Zip.Reduced.dll'))

    # HACK: We also need this on Windows
    if is_windows():
        robocopy(env.format('{root_dir}/Engine/Source/ThirdParty/FBX/2014.2.1/lib/vs2012/x64/release/libfbxsdk.dll'),
                 env.format('{root_dir}/Engine/Binaries/Win64/libfbxsdk.dll'))

    # Bootstrap if necessary
    if hasattr(env, 'bootstrap') and env.bootstrap:
        # Now generate project files
        if _ue4_generate_project(env) != 0:
            log_error("Error generating UE4 project files")
            return False

    # The Durango XDK does not support Visual Studio 2013 yet, so if UE4
    # detected it, it created VS 2012 project files and we have to use that
    # version to build the tools instead.
    vs_version = '12'
    try:
        for line in open(env.format(env.solution)):
            if '# Visual Studio 2012' in line:
                vs_version = '11'
                break
    except:
        pass

    # The main solution file
    solution = env.format(env.solution)

    # We’ll try to build all tools even in case of failure
    result = True

    # List of tools to build
    tools = []

    if env.target == 'tools':

        tools += [ 'UnrealFrontend',
                   'UnrealFileServer',
                   'ShaderCompileWorker', ]

        if env.platform != 'mac':
            tools += [ 'UnrealLightmass', ] # doesn’t build (yet?)

        if env.platform == 'linux':
            tools += [ 'CrossCompilerTool', ]

        if env.platform == 'win64':
            tools += [ 'DotNETUtilities',
                       'AutomationTool',
                       'PS4DevKitUtil',
                       'PS4MapFileUtil',
                       'XboxOnePDBFileUtil',
                       'SymbolDebugger',
                       'UnrealPak', ]

    # Some tools are necessary even when not building tools...
    if env.platform == 'ps4':
        if 'PS4MapFileUtil' not in tools: tools += [ 'PS4MapFileUtil' ]

    if env.platform == 'xboxone':
        if 'XboxOnePDBFileUtil' not in tools: tools += [ 'XboxOnePDBFileUtil' ]

    # Build tools from the main solution
    for tool in tools:
        if not _ue4_build_project(env, solution, tool,
                                  'Mac' if env.platform == 'mac'
                                  else 'Linux' if env.platform == 'linux'
                                  else 'Win64',
                                  'Development', vs_version, 'Build'):
            log_error("Could not build %s" % (tool, ))
            result = False

    # Build tools from other solutions or with other flags
    if env.target == 'tools':

        if not vsbuild(env.format('{root_dir}/Engine/Source/Programs/NetworkProfiler/NetworkProfiler.sln'),
                       'Any CPU', 'Development', None, vs_version, 'Build'):
            log_error("Could not build NetworkProfiler")
            result = False

        if env.platform != 'mac':
            # This also builds AgentInterface.dll, needed by SwarmInterface.sln
            if not vsbuild(env.format('{root_dir}/Engine/Source/Programs/UnrealSwarm/UnrealSwarm.sln'),
                           'Any CPU', 'Development', None, vs_version, 'Build'):
                log_error("Could not build UnrealSwarm")
                result = False

            if not vsbuild(env.format('{root_dir}/Engine/Source/Editor/SwarmInterface/DotNET/SwarmInterface.sln'),
                           'Any CPU', 'Development', None, vs_version, 'Build'):
                log_error("Could not build SwarmInterface")
                result = False

        # These tools seem to be Windows only for now
        if env.platform == 'win64':

            if not _ue4_build_project(env, solution, 'BootstrapPackagedGame',
                                      'Win64', 'Shipping', vs_version, 'Build'):
                log_error("Could not build BootstrapPackagedGame")
                result = False

            if not vsbuild(env.format('{root_dir}/Engine/Source/Programs/XboxOne/XboxOnePackageNameUtil/XboxOnePackageNameUtil.sln'),
                           'x64', 'Development', None, '11', 'Build'):
                log_error("Could not build XboxOnePackageNameUtil")
                result = False

    if not result:
        return result

    if env.target == 'game':
        if not _ue4_build_project(env, solution, env.game, env.ue4_build_platform,
                                  env.ue4_build_configuration, vs_version, 'Build'):
            return False

    if env.target == 'editor':
        if not _ue4_build_project(env, solution, env.game, env.ue4_build_platform,
                                  env.ue4_build_configuration + ' Editor', vs_version, 'Build'):
            return False

    return True


#
# Generate UE4 project files
#

def _ue4_generate_project(env):
    if is_windows():
        return call_process(env.root_dir, ['cmd', '/c', 'GenerateProjectFiles.bat'])
    else:
        return call_process(env.root_dir, ['/bin/sh', './GenerateProjectFiles.sh'])


#
# Helper commands for configuration sanitising
#

def get_ue4_build_config(config):
    d = { "debug"    : "Debug",
          "devel"    : "Development",
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
    d = { "ps4"     : "PS4",
          "xboxone" : "XBoxOne",
          "win64"   : "Win64",
          "win32"   : "Win32",
          "linux"   : "Linux", }
    if platform not in d:
        log_warning('Unsupported UE4 cook platform “%s”' % (platform))
        return None
    return d[platform]


#---------------------------------------------------------------------------
def _ue4_build_project(env, sln_file, project, build_platform,
                       configuration, vs_version, target = 'Rebuild'):

    if is_windows():
        return vsbuild(sln_file, build_platform, configuration,
                       project, vs_version, target)

    return call_process(env.root_dir,
                        ['/bin/sh', './Engine/Build/BatchFiles/%s/Build.sh' % (build_platform),
                         project, build_platform, configuration]) == 0


#---------------------------------------------------------------------------
def ue4_commandlet(env, commandlet, *args):
    cmdline = [sanitize_path(os.path.join(env.format(env.root_dir), "Engine/Binaries/Win64/UE4Editor.exe")),
                env.game,
                "-run=%s" % commandlet]

    cmdline += list(args)
    cmdline += ['-nopause', '-buildmachine', '-forcelogflush', '-unattended', '-noscriptcheck']

    return call_process('.', cmdline) == 0

