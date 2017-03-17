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
import nimp.summary

def load_config(env):
    ''' Loads Unreal specific configuration values on env before parsing
        command-line arguments '''
    env.is_ue4 = hasattr(env, 'project_type') and env.project_type is 'UE4'
    return True

def load_arguments(env):
    ''' Loads Unreal specific environment parameters. '''
    if hasattr(env, 'project_type') and env.project_type == 'UE4':
        return _ue4_load_arguments(env)

    return True

def build(env):
    ''' Builds an Unreal Engine Project. config and platform arguments should
        be set on environment in order to call this function. You can use
        `nimp.environment.add_arguments` and `nimp.build.add_arguments` to do
        so.'''
    if not _check_for_unreal(env):
        return False
    return _ue4_build(env)

def commandlet(env, command, *args, heartbeat = 0):
    ''' Runs an Unreal Engine commandlet. It can be usefull to run it through
        nimp as OutputDebugString will be redirected to standard output. '''
    if not _check_for_unreal(env):
        return False
    return _ue4_commandlet(env, command, *args, heartbeat = heartbeat)

def is_unreal4_available(env):
    ''' Returns a tuple containing unreal availability and a help text
        giving a reason of why it isn't if it's the case '''
    return env.is_ue4, ('No .nimp.conf configured for Unreal 4 was found in '
                        'this directory or one of its parents. Check that you '
                        'are launching nimp from inside an UE4 project directory'
                        ' and that you have a properly configured .nimp.conf. '
                        'Check documentation for more details on .nimp.conf.')
def _check_for_unreal(env):
    if not env.is_ue4:
        logging.error('This doesn\'t seems to be a supported project type.')
        logging.error('Check that you are launching nimp from an UE project')
        logging.error('directory, and that you have a .nimp.conf file in the')
        logging.error('project root directory (see documentation for further')
        logging.error('details)')
        return False
    return True

def _ue4_build(env):
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

    # Default to VS 2015, The Durango XDK does not support Visual Studio 2013 yet, so if UE4
    # detected it, it created VS 2012 project files and we have to use that
    # version to build the tools instead.
    vs_version = '14'
    try:
        for line in open(env.format(env.solution)):
            if ('# Visual Studio 2012' in line
                    or '# Visual Studio 11' in line):
                vs_version = '11'
                break
            if ('# Visual Studio 2013' in line
                    or '# Visual Studio 12' in line):
                vs_version = '12'
                break
            if ('# Visual Studio 2015' in line
                    or '# Visual Studio 14' in line):
                vs_version = '14'
                break
    except IOError:
        pass

    # The main solution file
    solution = env.format(env.solution)

    # We’ll try to build all tools even in case of failure
    success = True

    # List of tools to build
    tools = [ 'UnrealHeaderTool' ]

    # Some tools are necessary even when not building tools...
    need_ps4devkitutil = False
    need_ps4mapfileutil = env.platform == 'ps4'
    need_xboxonepdbfileutil = env.platform == 'xboxone'

    if env.target == 'tools':

        tools += [ 'UnrealFrontend',
                   'UnrealFileServer',
                   'ShaderCompileWorker',
                   'UnrealPak',
                   'CrashReportClient' ]

        if env.platform != 'mac':
            tools += [ 'UnrealLightmass', ] # doesn’t build (yet?)

        if env.platform == 'linux':
            tools += [ 'CrossCompilerTool', ]

        if env.platform == 'win64':
            tools += [ 'DotNETUtilities',
                       'AutomationTool',
                       'SymbolDebugger' ]
            need_ps4devkitutil = True
            need_ps4mapfileutil = True
            need_xboxonepdbfileutil = True

    # Some tools are necessary even when not building tools...
    if need_ps4devkitutil and os.path.exists(nimp.system.sanitize_path(env.format('{root_dir}/Engine/Source/Programs/PS4/PS4DevKitUtil/PS4DevKitUtil.csproj'))):
        tools += [ 'PS4DevKitUtil' ]

    if need_ps4mapfileutil and os.path.exists(nimp.system.sanitize_path(env.format('{root_dir}/Engine/Source/Programs/PS4/PS4MapFileUtil/PS4MapFileUtil.Build.cs'))):
        tools += [ 'PS4MapFileUtil' ]

    if need_xboxonepdbfileutil and os.path.exists(nimp.system.sanitize_path(env.format('{root_dir}/Engine/Source/Programs/XboxOne/XboxOnePDBFileUtil/XboxOnePDBFileUtil.Build.cs'))):
        tools += [ 'XboxOnePDBFileUtil' ]

    # Build tools from the main solution
    for tool in tools:
        if not _ue4_build_project(env, solution, tool,
                                  'Mac' if env.platform == 'mac'
                                  else 'Linux' if env.platform == 'linux'
                                  else 'Win64',
                                  'Shipping' if tool == 'CrashReportClient'
                                  else 'Development',
                                  vs_version, 'Build'):
            logging.error("Could not build %s", tool)
            success = False

    # Build tools from other solutions or with other flags
    if env.target == 'tools':

        if not nimp.build.vsbuild(env.format('{root_dir}/Engine/Source/Programs/NetworkProfiler/NetworkProfiler.sln'),
                                  'Any CPU', 'Development',
                                  vs_version=vs_version,
                                  target='Build'):
            logging.error("Could not build NetworkProfiler")
            success = False

        if not nimp.build.vsbuild(env.format('{root_dir}/Engine/Source/Programs/CrashReport/CrashReport.sln'),
                                  'Any CPU', 'Release',
                                  project='AutoReporter',
                                  vs_version=vs_version,
                                  target='Build'):
            logging.error("Could not build AutoReporter")
            success = False

        if env.platform != 'win64':
            # On Windows this is part of the main .sln, but not on Linux…
            if not nimp.build.vsbuild(env.format('{root_dir}/Engine/Source/Programs/AutomationTool/AutomationTool_Mono.sln'),
                                      'Any CPU', 'Development',
                                      vs_version=vs_version,
                                      target='Build'):
                logging.error("Could not build AutomationTool")
                success = False

        if env.platform != 'mac':
            # This also builds AgentInterface.dll, needed by SwarmInterface.sln
            if not nimp.build.vsbuild(env.format('{root_dir}/Engine/Source/Programs/UnrealSwarm/UnrealSwarm.sln'),
                                      'Any CPU', 'Development',
                                      vs_version=vs_version,
                                      target='Build'):
                logging.error("Could not build UnrealSwarm")
                success = False

            if not nimp.build.vsbuild(env.format('{root_dir}/Engine/Source/Editor/SwarmInterface/DotNET/SwarmInterface.sln'),
                                      'Any CPU', 'Development',
                                      vs_version=vs_version,
                                      target='Build'):
                logging.error("Could not build SwarmInterface")
                success = False

        # These tools seem to be Windows only for now
        if env.platform == 'win64':

            if not _ue4_build_project(env, solution, 'BootstrapPackagedGame',
                                      'Win64', 'Shipping', vs_version, 'Build'):
                logging.error("Could not build BootstrapPackagedGame")
                success = False

            tmp = env.format('{root_dir}/Engine/Source/Programs/XboxOne/XboxOnePackageNameUtil/XboxOnePackageNameUtil.sln')
            if os.path.exists(nimp.system.sanitize_path(tmp)):
                if not nimp.build.vsbuild(tmp, 'x64', 'Development',
                                          vs_version='11',
                                          target='Build') \
                   and not nimp.build.vsbuild(tmp, 'x64', 'Development',
                                              vs_version='14',
                                              target='Build'):
                    logging.error("Could not build XboxOnePackageNameUtil")
                    success = False

    if not success:
        return success

    if env.target == 'game':
        if not _ue4_build_project(env, solution, env.game, env.ue4_platform,
                                  env.ue4_config, vs_version, 'Build'):
            logging.error("Could not build game project")
            success = False

    if env.target == 'editor':
        if env.platform in ['linux', 'mac']:
            project = env.game + 'Editor'
            config = env.ue4_config
        else:
            project = env.game
            config = env.ue4_config + ' Editor'

        if not _ue4_build_project(env, solution, project, env.ue4_platform,
                                  config, vs_version, 'Build'):
            logging.error("Could not build editor project")
            success = False

    if success:
        nimp.environment.execute_hook('postbuild', env)

    return success

def _ue4_commandlet(env, command, *args, heartbeat = 0):
    ''' Runs an UE4 commandlet '''
    if nimp.system.is_windows():
        exe = 'Engine/Binaries/Win64/UE4Editor.exe'
    elif platform.system() == 'Darwin':
        exe = 'Engine/Binaries/Mac/UE4Editor'
    else:
        exe = 'Engine/Binaries/Linux/UE4Editor'

    cmdline = [nimp.system.sanitize_path(os.path.join(env.format(env.root_dir), exe)),
               env.game,
               '-run=%s' % command]

    cmdline += list(args)
    cmdline += ['-buildmachine', '-nopause', '-unattended', '-noscriptcheck']
    # Remove -forcelogflush because it slows down cooking
    # (https://udn.unrealengine.com/questions/330502/increased-cook-times-in-ue414.html)
    #cmdline += ['-forcelogflush']

    return nimp.system.call_process('.', cmdline, heartbeat = heartbeat) == 0


def _ue4_generate_project(env):
    if nimp.system.is_windows():
        return nimp.system.call_process(env.root_dir, ['cmd', '/c', 'GenerateProjectFiles.bat', '-2015'])
    else:
        return nimp.system.call_process(env.root_dir, ['/bin/sh', './GenerateProjectFiles.sh'])

def _ue4_build_project(env, sln_file, project, build_platform,
                       configuration, vs_version, target = 'Rebuild'):

    if nimp.system.is_windows():
        return nimp.build.vsbuild(sln_file, build_platform, configuration,
                                  project=project,
                                  vs_version=vs_version,
                                  target=target)

    if platform.system() == 'Darwin':
        host_platform = 'Mac'
    else:
        host_platform = 'Linux'

    return nimp.system.call_process(env.root_dir,
                                    ['/bin/sh', './Engine/Build/BatchFiles/%s/Build.sh' % (host_platform),
                                     project, build_platform, configuration]) == 0


def _ue4_load_arguments(env):
    ''' Sets some variables for use with unreal 4 '''
    def _get_ue4_config(config):
        configs = { "debug"    : "Debug",
                    "devel"    : "Development",
                    "test"     : "Test",
                    "shipping" : "Shipping", }
        if config not in configs:
            logging.warning('Unsupported UE4 build config “%s”', config)
            return None
        return configs[config]

    def _get_ue4_platform(in_platform):
        platforms = { "ps4"     : "PS4",
                      "xboxone" : "XboxOne",
                      "win64"   : "Win64",
                      "win32"   : "Win32",
                      "linux"   : "Linux",
                      "android" : "Android",
                      "mac"     : "Mac",
                      "ios"     : "iOS", }
        if in_platform not in platforms:
            logging.warning('Unsupported UE4 build platform “%s”', in_platform)
            return None
        return platforms[in_platform]

    if hasattr(env, 'platform'):
        env.ue4_platform = '+'.join(map(_get_ue4_platform, env.platform.split('+'))) #pylint: disable=bad-builtin

    if hasattr(env, 'configuration'):
        if env.configuration is None:
            env.configuration = 'devel'
        env.ue4_config = '+'.join(map(_get_ue4_config, env.configuration.split('+'))) #pylint: disable=bad-builtin

    if not hasattr(env, 'target') or env.target is None and env.is_ue4:
        if env.platform in ['win64', 'mac', 'linux']:
            env.target = 'editor'
        else:
            env.target = 'game'

    return True

def _cant_find_file(_, group_dict):
    assert 'asset' in group_dict
    asset_name = group_dict['asset']
    msg_str = ('This asset contains a reference to %s which is missing.'
               'You probably didn\'t fix references when deleting it, or '
               'you forgot to add it to source control.')
    return msg_str % asset_name

_MESSAGE_PATTERNS = [
    (re.compile(r'.*Can\'t find file.* \'\(?P<asset>[^\']\)\'.*'), _cant_find_file)
]

class _AssetSummary(object):
    def __init__(self, hints, asset_name):
        self._hints = hints
        self._asset_name = asset_name
        self._errors = set()
        self._warnings = set()

    def add_error(self, msg):
        """ Adds a message to this asset's summary """
        self._add_message(msg, self._errors)

    def add_warning(self, msg):
        """ Adds a message to this asset's summary """
        self._add_message(msg, self._warnings)

    def write(self, destination):
        """ Writes summary for this asset into destination """
        if len(self._errors) == 0 and len(self._warnings) == 0:
            return
        destination.write('%s :\n' % self._asset_name)
        for error in self._errors:
            destination.write(' * ERROR   : %s\n' % error)
        for warning in self._warnings:
            destination.write(' * WARNING : %s\n' % warning)

    def _add_message(self, msg, destination):
        for message_format, patterns in self._hints.items():
            for pattern in patterns:
                match = pattern.match(msg)
                if match is not None:
                    try:
                        group_dict = match.groupdict()
                        message = message_format.format(**group_dict)
                        destination.add(message)
                        return
                    finally:
                        pass

        destination.add('Unknown error message : %s' % msg)

class UnrealSummaryHandler(nimp.summary.SummaryHandler):
    """ Default summary handler, showing one line by error / warning and
    adding three lines of context before / after errors """
    def __init__(self, env):
        super().__init__(env)
        self._summary = ''
        self._asset_summaries = {}
        self._hints = {}
        self._load_asset_patterns = {}
        self._current_asset = None
        self._unknown_asset = _AssetSummary(self._hints, 'Unknown location')
        load_asset_patterns = [
            r'.*\[\d+\/\d+\] Loading [\.|\/]*(?P<asset>.*)\.\.\.$'
        ]

        self._load_asset_patterns = [
            re.compile(it) for it in load_asset_patterns
        ]

        if hasattr(env, 'unreal_summary_hints'):
            for message_format, patterns in env.unreal_summary_hints.items():
                self._hints[message_format] = []
                for pattern in patterns:
                    try:
                        self._hints[message_format].append(re.compile(pattern))
                    #pylint: disable=broad-except
                    except Exception as ex:
                        logging.error('Error while compiling pattern %s: %s',
                                      pattern, ex)

    def _add_notif(self, msg):
        self._update_current_asset(msg)

    def _add_warning(self, msg):
        current_asset = self._update_current_asset(msg)
        current_asset.add_warning(msg)

    def _add_error(self, msg):
        current_asset = self._update_current_asset(msg)
        current_asset.add_error(msg)

    def _write_summary(self, destination):
        ''' Writes summary to destination '''
        for _, asset_summary in self._asset_summaries.items():
            asset_summary.write(destination)

        self._unknown_asset.write(destination)

    def _update_current_asset(self, msg):
        for pattern in self._load_asset_patterns:
            match = pattern.match(msg)
            if match is not None:
                group_dict = match.groupdict()
                assert 'asset' in group_dict
                asset_name = group_dict['asset']
                if asset_name not in self._asset_summaries:
                    asset_summary = _AssetSummary(self._hints, asset_name)
                    self._asset_summaries[asset_name] = asset_summary

                self._current_asset = self._asset_summaries[asset_name]
                return self._current_asset

        if self._current_asset is not None:
            return self._current_asset

        return self._unknown_asset
