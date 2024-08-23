# -*- coding: utf-8 -*-
# Copyright (c) 2014-2021 Dontnod Entertainment

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

'''Command to run executables or special commands'''

import abc
import logging
import re
import os
import shutil
import subprocess

import nimp.command
import nimp.unreal
import nimp.sys.process
from nimp.sys.platform import create_platform_desc
from nimp.base_commands.package import Package


class Run(nimp.command.CommandGroup):
    '''Run executables, hooks, and commandlets'''

    def __init__(self):
        super(Run, self).__init__([_Hook(), _Commandlet(), _Unreal_cli(), _Exec_cmd(), _Staged(), _Package()])

    def is_available(self, env):
        return True, ''


class RunCommand(nimp.command.Command):
    def __init__(self):
        super(RunCommand, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'dry_run')
        parser.add_argument('command_name', help='Command name to run', metavar='<command>')
        parser.add_argument('parameters', help='Arguments of the command to run', metavar='<argument>...', nargs="*")
        return True

    def is_available(self, env):
        return True, ''


class _Hook(RunCommand):
    '''Runs a hook'''

    def __init__(self):
        super(_Hook, self).__init__()

    def run(self, env):
        if len(env.parameters) != 0:
            logging.error('Too many arguments')
            return False
        hook = env.command_name
        return nimp.environment.execute_hook(hook, env)


class BaseUnrealCli(RunCommand):
    '''Base for unreal cli type commands'''

    def __init__(self):
        super().__init__()

    def configure_arguments(self, env, parser):
        super().configure_arguments(env, parser)
        nimp.command.add_common_arguments(parser, 'slice_job')
        nimp.utils.p4.add_arguments(parser)

    def is_available(self, env):
        if not nimp.unreal.is_unreal_available(env):
            return False, 'Not an Unreal Engine project'
        return True, ''

    def run_unreal_command(self, env, args):
        pass

    def run(self, env):
        args = env.parameters + nimp.unreal.get_args_for_unreal_cli(env)
        args = [env.format(arg) for arg in args]
        return self.run_unreal_command(env, args)


class _Commandlet(BaseUnrealCli):
    '''Runs an unreal commandlet'''

    def run_unreal_command(self, env, args):
        return nimp.unreal.commandlet(env, env.command_name, *args)


class _Unreal_cli(BaseUnrealCli):
    '''Runs an unreal cli command'''

    def run_unreal_command(self, env, args):
        return nimp.unreal.unreal_cli(env, env.command_name, *args)


class _Exec_cmd(RunCommand):
    '''Runs executables on the local host'''

    def __init__(self):
        super(_Exec_cmd, self).__init__()

    def run(self, env):
        if env.verbose:
            logging.debug("Will run: %s" % shutil.which(env.command_name))
        cmdline = [env.command_name]
        for arg in env.parameters:
            cmdline.append(env.format(arg))

        nimp.environment.execute_hook('prerun', env)
        ret = nimp.sys.process.call(cmdline, dry_run=env.dry_run)
        nimp.environment.execute_hook('postrun', env)

        return ret == 0


class ConsoleGameCommand(nimp.command.Command):
    def __init__(self, buildbot_directory_ending, local_directory):
        super(ConsoleGameCommand, self).__init__()
        self.buildbot_directory_ending = buildbot_directory_ending
        self.local_directory = local_directory

    def configure_arguments(self, env, parser):
        super(ConsoleGameCommand, self).configure_arguments(env, parser)
        nimp.command.add_common_arguments(parser, 'platform', 'configuration')

        parser.add_argument(
            '--fetch', metavar='<path | CL# | "latest">', help='copies the game to the default location on this machine'
        )

        if shutil.which('robocopy'):
            restartable_fetch_help = "If '--fetch' is provided, will invoke robocopy with '/Z' (Recommended for users with poor or unstable connections)"
        else:
            restartable_fetch_help = 'This option requires Robocopy which is unavailable on your system'

        # Basic cp does not handle restartable copy
        parser.add_argument('--restartable-fetch', action="store_true", help=restartable_fetch_help)

        parser.add_argument('--outdir', nargs='?', default='local', help='output directory for fetch')

        parser.add_argument(
            '--deploy',
            nargs='?',
            const='local',
            metavar='<path | CL# | "latest">',
            help="deploy the game to a devkit. If empty, deploys from the game's 'Saved' directory\
                                  WARNING: if passing a CL number or 'latest', be aware that\
                                  the game will be downloaded from B:\\, then reuploaded to the devkit!!\
                                  Avoid doing this over the VPN",
        )

        parser.add_argument(
            '--launch', nargs='?', const='default', metavar='<package_name>', help='launch the game on a devkit'
        )

        parser.add_argument('--device', metavar='<host>', help='set target device')
        parser.add_argument('-v', '--variant', metavar="<variant_name>", help="name of variant")

    def is_available(self, env):
        return True, ''

    def run(self, env):
        self.platform_directory = nimp.sys.platform.create_platform_desc(env.platform).unreal_cook_name

        if env.fetch:
            return self.fetch(env)
        if env.deploy:
            return self.deploy(env)
        if env.launch:
            return self._launch(env)
        return False

    def fetch(self, env):
        env.fetch = self.get_path_from_parameter(env.fetch, env)
        if env.outdir == 'local':
            # We don't use get_local_path here as that would return the config subdirectory (e.g. Saved/StagedBuilds/Development)
            env.outdir = f'{env.uproject_dir}/Saved/{self.local_directory}/{self.platform_directory}'

        if shutil.which('robocopy'):
            return self.fetch_with_robocopy(env)
        else:
            return self.fetch_with_copy(env)

    def fetch_with_robocopy(self, env):
        logging.info(f'Mirroring {env.fetch} into {env.outdir}')
        cmdline = ['robocopy', '/MIR', '/R:5', '/W:5', '/TBD', '/NJH', '/ETA', '/MT', '/J']
        if env.restartable_fetch:
            cmdline.append('/Z')
        cmdline += [env.fetch, env.outdir]
        logging.info('Running %s', cmdline)
        if env.dry_run:
            return True
        result = subprocess.call(
            cmdline
        )  # Call subprocess directly to allow "dynamic" output (with progress percentage)
        return result <= 1  # 0: nothing to copy. 1: some files were copied

    def fetch_with_copy(self, env):
        if os.path.exists(env.outdir):
            logging.warning(f'{env.outdir} exists. Deleting it.')
            if not env.dry_run:
                shutil.rmtree(env.outdir)
        logging.info(f'Copying from {env.fetch} to {env.outdir}')
        if env.dry_run:
            return True
        return shutil.copytree(env.fetch, env.outdir)

    def deploy(self, env):
        env.deploy = self.get_path_from_parameter(env.deploy, env)
        if not os.path.isdir(env.deploy):
            raise FileNotFoundError(f'Invalid path / could not find a valid pkg file in {env.deploy}')
        return self._deploy(env)

    def get_path_from_parameter(self, param, env):
        path = param
        if str.isdigit(param):
            path = self.fetch_pkg_by_revision(env, param)
        # if 'latest' was provided, fetch latest package uploaded to /b/
        elif param.lower() == 'latest':
            path = self.fetch_pkg_latest(env)
        elif param == 'local':
            path = self.get_local_path(env)

        # Depending on the game and platform, we may have a path like
        #   B:\pg0-alf\main\packages\fullgame\pg0-alf-main-fullgame-1146142-xsx-staged\XSX
        # In that case, get rid of the trailing "\XSX"
        platform_desc = create_platform_desc(env.platform)
        cook_platform = platform_desc.unreal_cook_name
        platform_intermediate_directory = os.path.join(path, cook_platform)
        if os.path.exists(platform_intermediate_directory):
            path = platform_intermediate_directory
        return path

    def get_local_path(self, env):
        path = os.path.join(env.uproject_dir, 'Saved', self.local_directory, self.platform_directory)
        config_path = os.path.join(path, env.unreal_config)
        if os.path.exists(config_path):
            return config_path
        return path

    def get_artifact_repository(self, env, rev):
        return env.format(
            f'{env.artifact_repository_destination}/{env.artifact_collection[self.buildbot_directory_ending]}',
            target=env.variant,
            revision=rev,
        )

    def fetch_pkg_by_revision(self, env, rev):
        if not env.variant:
            raise RuntimeError('"variant" parameter is required to fetch remote packages')

        logging.info(f'Looking for a {env.platform} test package at CL#{rev}')
        artifact_repository = self.get_artifact_repository(env, rev)
        return nimp.system.sanitize_path(artifact_repository)

    def fetch_pkg_latest(self, env):
        if not env.variant:
            raise RuntimeError('"variant" parameter is required to fetch remote packages')

        artifact_repository = self.get_artifact_repository(env, '<revision>')  # Path for a given revision
        parent_directory = os.path.dirname(
            nimp.system.sanitize_path(artifact_repository)
        )  # Path containing all the revisions
        logging.info(f'Looking for latest {env.platform} package in {parent_directory}')

        pkg_directory_format = os.path.basename(artifact_repository)
        pkg_directory_format = pkg_directory_format.replace('<revision>', r'(\d+)')
        regex = re.compile(pkg_directory_format)

        rev = '0'
        for d in os.listdir(parent_directory):
            m = regex.match(d)
            if m and m.group(1) > rev:
                rev = m.group(1)

        return self.fetch_pkg_by_revision(env, rev)

    @abc.abstractmethod
    def _deploy(self, env):
        pass

    @abc.abstractmethod
    def _launch(self, env):
        pass


class _Staged(ConsoleGameCommand):
    '''Deploys and runs staged console builds'''

    def __init__(self):
        super(_Staged, self).__init__('staged', 'StagedBuilds')

    def _deploy(self, env):
        # ./RunUAT.sh BuildCookRun -project=ALF -platform=xsx -skipcook -skipstage -deploy [-configuration=Development] [-device=IP]

        absolute_path = os.path.abspath(
            env.deploy + '/..'
        )  # UAT expects this to point to StagedBuilds directory, not StagedBuilds/Platform

        with Package.configure_variant(env, nimp.system.standardize_path(env.format('{uproject_dir}'))):
            cmdline = [
                os.path.join(env.root_dir, 'Game', 'RunUAT.bat'),
                'BuildCookRun',
                '-project=' + env.game,
                '-platform=' + env.platform,
                '-configuration=' + env.unreal_config,
                '-stagingdirectory=' + absolute_path,
                '-skipcook',
                '-skipstage',
                '-deploy',
            ]
            if env.device:
                cmdline.append('-device=' + env.device)

            result = nimp.sys.process.call(cmdline, dry_run=env.dry_run)
            return result == 0

    def _launch(self, env):
        # ./RunUAT.sh BuildCookRun -project=ALF -platform=xsx -skipcook -skipstage -deploy -run [-device=IP]

        if env.launch == 'default':
            env.launch = 'local'
        env.launch = self.get_path_from_parameter(env.launch, env)
        absolute_path = os.path.abspath(
            env.launch + '/..'
        )  # UAT expects this to point to StagedBuilds directory, not StagedBuilds/Platform

        cmdline = [
            os.path.join(env.root_dir, 'Game', 'RunUAT.bat'),
            'BuildCookRun',
            '-project=' + env.game,
            '-platform=' + env.platform,
            '-configuration=' + env.unreal_config,
            '-stagingdirectory=' + absolute_path,
            '-skipcook',
            '-skipstage',
            '-deploy',
            '-run',
        ]
        if env.device:
            cmdline.append('-device=' + env.device)

        result = nimp.sys.process.call(cmdline, dry_run=env.dry_run)
        return result == 0


class _Package(ConsoleGameCommand):
    '''Deploys and runs console packages'''

    def __init__(self):
        super(_Package, self).__init__('package', 'Packages')

    def _deploy(self, env):
        platform_desc = create_platform_desc(env.platform)
        return platform_desc.install_package(env.deploy, env)

    def _launch(self, env):
        platform_desc = create_platform_desc(env.platform)
        if env.launch == 'default':
            env.launch = None
        return platform_desc.launch_package(env.launch, env)
