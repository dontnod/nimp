# -*- coding: utf-8 -*-
# Copyright (c) 2014-2019 Dontnod Entertainment

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

'''Unreal Engine related stuff'''

import json
import logging
import os
import platform
import re
import glob
from packaging import version

import nimp.build
import nimp.system
import nimp.sys.platform
import nimp.sys.process
import nimp.summary

from nimp.sys.platform import create_platform_desc_unreal


def load_config(env):
    '''Loads Unreal specific configuration values on env before parsing
    command-line arguments'''
    unreal_file = 'Engine/Build/Build.version'
    unreal_dir = None

    unreal_base_paths = [
        'UE',
        'UE4',
        '',
    ]
    for unreal_path in unreal_base_paths:
        unreal_dir = nimp.system.find_dir_containing_file(os.path.join(unreal_path, unreal_file))
        if unreal_dir:
            unreal_dir = os.path.join(unreal_dir, unreal_path)
            break

    if not unreal_dir:
        env.is_unreal = env.is_ue4 = env.is_ue5 = False
        env.is_dne_legacy_ue4 = True
        return True

    with open('%s/%s' % (unreal_dir, unreal_file)) as version_file:
        data = json.load(version_file)
        env.unreal_major = data['MajorVersion']
        env.unreal_minor = data['MinorVersion']
        env.unreal_patch = data['PatchVersion']
        env.unreal_version = float(f'{data["MajorVersion"]}.{data["MinorVersion"]}')
        env.unreal_full_version = version.parse(
            str(f'{data["MajorVersion"]}.{data["MinorVersion"]}.{data["PatchVersion"]}')
        )
        if env.unreal_major == 4:  # Legacy, for older UE4 project conf
            env.ue4_major = env.unreal_major
            env.ue4_minor = env.unreal_minor
            env.ue4_patch = env.unreal_patch

    env.is_unreal = True
    env.is_ue4 = False
    env.is_ue5 = False
    if env.unreal_major == 4:
        env.is_ue4 = env.is_unreal
        env.is_ue5 = False
    if env.unreal_major == 5:
        env.is_ue5 = env.is_unreal
        env.is_ue4 = False
    env.unreal_dir = unreal_dir
    env.unreal_root_path = os.path.basename(unreal_dir)
    if env.is_ue4:  # legacy compat for old conf
        env.ue4_dir = unreal_dir
    # Backward compatibility (TODO: remove later)
    if not hasattr(env, 'is_dne_legacy_ue4'):
        env.is_dne_legacy_ue4 = env.unreal_version < 4.22

    if not hasattr(env, 'root_dir') or env.root_dir is None:
        env.root_dir = os.path.normpath(unreal_dir)

    # The host platform
    env.unreal_host_platform = (
        'Win64' if nimp.sys.platform.is_windows() else 'Mac' if platform.system() == 'Darwin' else 'Linux'
    )
    if env.is_ue4:  # legacy for old conf
        env.ue4_host_platform = (
            'Win64' if nimp.sys.platform.is_windows() else 'Mac' if platform.system() == 'Darwin' else 'Linux'
        )

    # Forward compatibility (TODO: remove later when all configuration files use uproject)
    if hasattr(env, 'game'):
        env.uproject = env.format(env.game)
    if hasattr(env, 'game_dir'):
        env.uproject_dir = env.format(env.game_dir)

    # If no uproject information is provided, look for one
    if not hasattr(env, 'uproject_dir') or not hasattr(env, 'uproject'):
        patterns = set()
        for upd in glob.glob(unreal_dir + '/*.uprojectdirs'):
            with open(upd, 'r') as upd_file:
                for pattern in upd_file.readlines():
                    if pattern.startswith(';'):
                        continue
                    patterns.add(pattern.strip())
        ufiles = set()
        for pat in patterns:
            for ufile in glob.glob('%s/%s/*/*.uproject' % (unreal_dir, pat)):
                ufiles.add(os.path.normpath(ufile.strip()))

        cwd = os.getcwd()
        for ufile in ufiles:
            uproject = os.path.splitext(os.path.basename(ufile))[0]
            if hasattr(env, '_uproject'):  # --uproject case, check against declared uprojects
                if not hasattr(env, '_uproject_path'):  # param not valid, bail out
                    continue
                if uproject == env._uproject and ufile.lower().endswith(env._uproject_path.lower()):
                    env.uproject = env._uproject  # not sure this is useful - wip
                    env.uproject_dir = os.path.dirname(ufile)
            else:
                # try confirming uproject based off directory hints
                search_pattern = re.compile(
                    r'[\\|/]pg[\d][\d]?-%s-[\w.-]*?[\\|/].*[\\|/]Game[\\|/]%s[\\|/]?|[\\|/]Game[\\|/]%s[\\|/]?'
                    % (uproject, uproject, uproject),
                    re.IGNORECASE,
                )
                match = re.findall(search_pattern, cwd)
                if len(match) > 0:
                    env.uproject = uproject
                # Prefer anything over template and engine test directories as default uproject
                prefixes = ['TP_', 'FP_', 'EngineTest']
                if not hasattr(env, 'uproject') or any(prefix in env.uproject for prefix in prefixes):
                    env.uproject = uproject
                if uproject == env.uproject:
                    env.uproject_dir = os.path.dirname(ufile)

    # Do not throw here, as it *could* be on purpose to not have any uproject
    # if not hasattr(env, 'uproject_dir'):
    #    raise KeyError('No uproject found.')

    # Do not throw here, because our buildbot setup uses --uproject everywhere, including
    # when the repository is not yet set up.
    # if hasattr(env, '_uproject') and not hasattr(env, 'uproject_dir'):
    #    raise KeyError('Uproject not found : %s. Possible uprojects : ' % (env._uproject) +
    #                   ', '.join('%s' % os.path.splitext(os.path.basename(ufile))[0] + '/' + os.path.basename(ufile) for ufile in ufiles))

    # Backwards compatibility (TODO: remove later)
    if hasattr(env, 'uproject'):
        env.game = env.uproject
    if hasattr(env, 'uproject_dir'):
        env.game_dir = env.uproject_dir

    if not hasattr(env, 'unreal_exe_name') or env.unreal_exe_name is None:
        env.unreal_exe_name = _set_unreal_exe_name(env)

    if not hasattr(env, 'unreal_loadlist') or env.unreal_loadlist is None:
        env.unreal_loadlist = nimp.system.sanitize_path(f'{env.root_dir}/.nimp/loadlist')
        env.unreal_loadlist_abspath = nimp.system.sanitize_path(os.path.abspath(env.unreal_loadlist))

    return True


def load_arguments(env):
    '''Loads Unreal specific environment parameters.'''

    if env.is_unreal:
        if not hasattr(env, 'platform') or env.platform is None:
            if nimp.sys.platform.is_windows():
                env.platform = 'win64'
            elif nimp.sys.platform.is_osx():
                env.platform = 'mac'
            else:
                env.platform = 'linux'

    # This is safe even when we failed to detect Unreal
    _unreal_sanitize_arguments(env)
    _unreal_set_env(env)

    if env.is_unreal:
        if not hasattr(env, 'target') or env.target is None:
            if env.platform in ['win64', 'mac', 'linux']:
                env.target = 'editor'
            else:
                env.target = 'game'

    return True


# TODO: deprecate this in favour of env.unreal_host_platform
def get_host_platform():
    '''Get the Unreal platform for the host platform'''
    if platform.system() == 'Windows':
        return 'Win64'
    if platform.system() == 'Linux':
        return 'Linux'
    if platform.system() == 'Darwin':
        return 'Mac'
    raise ValueError('Unsupported platform: ' + platform.system())


def get_configuration_platform(unreal_platform):
    '''Gets the platform name used for configuration files'''
    # From PlatformProperties IniPlatformName
    return create_platform_desc_unreal(unreal_platform).unreal_config_name


def get_cook_platform(unreal_platform):
    '''Gets the platform name used for cooking assets'''
    # From Automation GetCookPlatform
    return create_platform_desc_unreal(unreal_platform).unreal_cook_name


def commandlet(env, command, *args, heartbeat=0):
    '''Runs an Unreal Engine commandlet. It can be usefull to run it through
    nimp as OutputDebugString will be redirected to standard output.'''
    if not _check_for_unreal(env):
        return False
    return _unreal_commandlet(env, command, *args, heartbeat=heartbeat)


def unreal_cli(env, *args, heartbeat=0, commandlet=None):
    '''Runs an Unreal CLI exe'''
    if not _check_for_unreal(env):
        return False
    return _unreal_cli(env, *args, heartbeat=heartbeat, commandlet=commandlet)


def is_unreal_available(env):
    '''Returns a tuple containing unreal availability and a help text
    giving a reason of why it isn't if it's the case'''
    return env.is_unreal, (
        'No .nimp.conf configured for Unreal was found in '
        'this directory or one of its parents. Check that you '
        'are launching nimp from inside an UE project directory '
        'and that you have a properly configured .nimp.conf. '
        'Check documentation for more details on .nimp.conf.'
    )


def is_unreal4_available(env):
    '''Legacy UE4 projects
    Returns a tuple containing unreal availability and a help text
    giving a reason of why it isn't if it's the case'''
    return env.is_ue4, (
        'No .nimp.conf configured for Unreal 4 was found in '
        'this directory or one of its parents. Check that you '
        'are launching nimp from inside an UE4 project directory'
        ' and that you have a properly configured .nimp.conf. '
        'Check documentation for more details on .nimp.conf.'
    )


def _check_for_unreal(env):
    if not env.is_unreal:
        logging.error('This doesn\'t seems to be a supported project type.')
        logging.error('Check that you are launching nimp from an UE project')
        logging.error('directory, and that you have a .nimp.conf file in the')
        logging.error('project root directory (see documentation for further')
        logging.error('details)')
        return False
    return True


def _unreal_cli(env, *args, heartbeat=0, commandlet=None):
    '''Runs an Unreal command line'''

    exe = '{unreal_dir}/Engine/Binaries/{unreal_host_platform}/{unreal_exe_name}-cmd.exe'
    cmdline = [nimp.system.sanitize_path(env.format(exe)), env.game]

    if commandlet:
        cmdline.append(f'-run={commandlet}')
    cmdline.extend(args)
    cmdline.extend(get_default_args_for_cli(env))

    return nimp.sys.process.call(cmdline, heartbeat=heartbeat, dry_run=env.dry_run) == 0


def _unreal_commandlet(env, command, *args, heartbeat=0):
    '''Runs an Unreal commandlet'''

    exe = '{unreal_dir}/Engine/Binaries/{unreal_host_platform}/{unreal_exe_name}.exe'
    cmdline = [nimp.system.sanitize_path(env.format(exe)), env.game, f'-run={command}']

    cmdline.extend(args)
    cmdline.extend(get_default_args_for_cli(env))

    return nimp.sys.process.call(cmdline, heartbeat=heartbeat, dry_run=env.dry_run) == 0


def _unreal_sanitize_arguments_for_retro_compat(env, *params):
    '''convert one item list param to string, for legacy'''
    for param in params:
        if hasattr(env, param):
            env_param = getattr(env, param)
            if env_param is not None:
                setattr(env, param, env_param[0] if isinstance(env_param, list) and len(env_param) == 1 else env_param)


def _unreal_sanitize_arguments(env):
    # some params in build command can now be a list of strings instead of one string
    _unreal_sanitize_arguments_for_retro_compat(env, 'platform', 'configuration', 'target')

    if hasattr(env, "platform") and env.platform is not None:
        env.is_microsoft_platform = False
        env.is_sony_platform = False
        env.is_nintendo_platform = False
        env.is_mobile_platform = False

        platform_descs = [nimp.sys.platform.create_platform_desc(p) for p in env.platform.split('+')]

        # Set env.is_ps4, env.is_linux, etc. to True for platforms we target
        for p in platform_descs:
            setattr(env, f'is_{p.name}', True)
            env.is_microsoft_platform = env.is_microsoft_platform or p.is_microsoft
            env.is_sony_platform = env.is_sony_platform or p.is_sony
            env.is_nintendo_platform = env.is_nintendo_platform or p.is_nintendo
            env.is_mobile_platform = env.is_mobile_platform or p.is_mobile

        # XXX: track usage of these variables and replace them with the correct name
        env.is_ps3 = False
        env.is_x360 = False
        env.is_xone = env.is_xboxone

        if env.is_unreal:
            env.platform = '+'.join(map(lambda x: x.name, platform_descs))

    if hasattr(env, 'configuration') and env.configuration is not None:

        def sanitize_config(config):
            '''Sanitizes config'''
            std_configs = {
                'debug': 'debug',
                'devel': 'devel',
                'release': 'release',
                'test': 'test',
                'shipping': 'shipping',
            }

            if config.lower() not in std_configs:
                return ""
            return std_configs[config.lower()]

        unreal_configuration = '+'.join(map(sanitize_config, env.configuration.split('+')))

        if env.is_unreal:
            env.configuration = unreal_configuration


def _unreal_set_env(env):
    '''Sets some variables for use with Unreal'''

    def _get_unreal_config(config):
        configs = {
            "debug": "Debug",
            "devel": "Development",
            "test": "Test",
            "shipping": "Shipping",
        }
        if config not in configs:
            if env.is_unreal:
                logging.warning('Unsupported Unreal build config "%s"', config)
            return None
        return configs[config]

    def _get_unreal_platform(in_platform):
        if not env.is_unreal:
            return in_platform
        return nimp.sys.platform.create_platform_desc(in_platform).unreal_name

    if hasattr(env, 'platform') and env.platform is not None:
        platform_list = list(map(_get_unreal_platform, env.platform.split('+')))
        if None not in platform_list:
            env.unreal_platform = '+'.join(platform_list)
            if env.is_ue4:
                env.ue4_platform = '+'.join(platform_list)

    # Transform configuration list, default to 'devel'
    if hasattr(env, 'configuration') and env.configuration is not None:
        config = env.configuration
    else:
        config = 'devel'
    config_list = list(map(_get_unreal_config, config.split('+')))
    if None not in config_list:
        env.unreal_config = '+'.join(config_list)
        if env.is_ue4:
            env.ue4_config = '+'.join(config_list)


def _cant_find_file(_, group_dict):
    assert 'asset' in group_dict
    asset_name = group_dict['asset']
    msg_str = (
        'This asset contains a reference to %s which is missing.'
        'You probably didn\'t fix references when deleting it, or '
        'you forgot to add it to source control.'
    )
    return msg_str % asset_name


_MESSAGE_PATTERNS = [(re.compile(r'.*Can\'t find file.* \'\(?P<asset>[^\']\)\'.*'), _cant_find_file)]


class _AssetSummary:
    def __init__(self, hints, asset_name):
        self._hints = hints
        self._asset_name = asset_name
        self._errors = set()
        self._warnings = set()

    def get_errors(self):
        return self._errors

    def get_warnings(self):
        return self._warnings

    def add_error(self, msg):
        """Adds a message to this asset's summary"""
        self._add_message(msg, self._errors)

    def add_warning(self, msg):
        """Adds a message to this asset's summary"""
        self._add_message(msg, self._warnings)

    def write(self, destination):
        """Writes summary for this asset into destination"""
        if not self._errors and not self._warnings:
            return
        destination.write('%s :\n' % self._asset_name)
        for error in self._errors:
            destination.write(' * ERROR   : %s\n' % error)
        for warning in self._warnings:
            destination.write(' * WARNING : %s\n' % warning)

        destination.write('\n')

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

        destination.add(msg)


def _set_unreal_exe_name(env):
    unreal_exe_name = 'UnrealEditor'
    if env.unreal_major == 4:
        unreal_exe_name = 'UE4Editor'
    # Exe name is <game>Editor in case we set uniqueBuildEnv
    _is_unique_build_env = hasattr(env, 'uniqueBuildEnvironment') and env.uniqueBuildEnvironment['is_enabled']
    if _is_unique_build_env:
        unreal_exe_name = env.game + 'Editor'
    return unreal_exe_name


class UnrealSummaryHandler(nimp.summary.SummaryHandler):
    """Default summary handler, showing one line by error / warning and
    adding three lines of context before / after errors"""

    def __init__(self, env):
        super().__init__(env)
        self._asset_summaries = {}
        self._hints = {}
        self._load_asset_patterns = {}
        self._current_asset = None
        self._unknown_asset = _AssetSummary(self._hints, 'Unknown location')
        load_asset_patterns = [r'.*\[\d+\/\d+\] Loading [\.|\/]*(?P<asset>.*)\.\.\.$']

        self._load_asset_patterns = [re.compile(it) for it in load_asset_patterns]

        if hasattr(env, 'unreal_summary_hints'):
            for message_format, patterns in env.unreal_summary_hints.items():
                self._hints[message_format] = []
                for pattern in patterns:
                    try:
                        self._hints[message_format].append(re.compile(pattern))
                    # pylint: disable=broad-except
                    except Exception as ex:
                        logging.error('Error while compiling pattern %s: %s', pattern, ex)

    def _add_notif(self, msg):
        self._update_current_asset(msg)

    def _add_msg(self, notif_lvl, msg):
        current_asset = self._update_current_asset(msg)
        if notif_lvl == 'error':
            current_asset.add_error(msg)
        else:
            current_asset.add_warning(msg)

    def _write_summary(self, destination):
        '''Writes summary to destination'''
        for _, asset_summary in self._asset_summaries.items():
            asset_summary.write(destination)

        self._unknown_asset.write(destination)

    def has_errors(self):
        '''Returns true if errors were emitted during program execution'''
        return len(self._unknown_asset.get_errors()) > 0

    def has_warnings(self):
        '''Returns true if warnings were emitted during program execution'''
        return len(self._unknown_asset.get_warnings()) > 0

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


def get_default_args_for_cli(env):
    '''Returns reasonable default arguments for both Unreal Commandlet and Unreal Cmd'''
    yield '-buildmachine'
    yield '-nopause'
    yield '-unattended'
    yield '-noscriptcheck'
    # Remove -forcelogflush because it slows down cooking
    # (https://udn.unrealengine.com/questions/330502/increased-cook-times-in-ue414.html)
    # yield '-forcelogflush'
    yield '-locallogtimes'

    if (ddc_env_override := os.getenv("UE-DDC")) is not None:
        yield f"-DDC={ddc_env_override}"


def get_p4_args_for_commandlet(env):
    p4_args_for_commandlet = []
    if env.has_attribute('nop4submit'):
        p4_args_for_commandlet.append('-DisableSCCSubmit')
    if env.has_attribute('p4port'):
        p4_args_for_commandlet.append('-P4Port=%s' % env.p4port)
    if env.has_attribute('p4user'):
        p4_args_for_commandlet.append('-P4User=%s' % env.p4user)
    if env.has_attribute('p4pass'):
        p4_args_for_commandlet.append('-P4Passwd=%s' % env.p4pass)
    if env.has_attribute('p4client'):
        p4_args_for_commandlet.append('-P4Client=%s' % env.p4client)
    if len(p4_args_for_commandlet) > 0:
        p4_args_for_commandlet.append('-SCCProvider=Perforce')
    if getattr(env, "auto_submit", False):
        p4_args_for_commandlet.append('-AutoSubmit')
    if getattr(env, "auto_checkout", False):
        p4_args_for_commandlet.append('-AutoCheckout')
    return p4_args_for_commandlet


def get_args_for_unreal_cli(env):
    args_for_commandlet = []
    args_for_commandlet.extend(get_p4_args_for_commandlet(env))
    if env.has_attribute('slice_job_index') and env.has_attribute('slice_job_count'):
        args_for_commandlet.append('-DNESlicer')
        args_for_commandlet.append(f'-SliceJobIndex={env.slice_job_index}')
        args_for_commandlet.append(f'-SliceJobCount={env.slice_job_count}')
    return args_for_commandlet
