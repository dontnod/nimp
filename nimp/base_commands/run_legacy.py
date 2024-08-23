# -*- coding: utf-8 -*-
# Copyright (c) 2014-2022 Dontnod Entertainment

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
import argparse
import json
import logging
import re
import os
import shutil
import subprocess

import nimp.command
import nimp.unreal
import nimp.sys.process
import nimp.utils.p4
from nimp.sys.platform import create_platform_desc


class RunLegacy(nimp.command.CommandGroup):
    '''Run executables, hooks, and commandlets'''

    def __init__(self):
        super(RunLegacy, self).__init__([_Hook(), _Commandlet(), _Unreal_cli(), _Exec_cmds(), _Staged(), _Package()])

    def is_available(self, env):
        return True, ''


class RunLegacyCommand(nimp.command.Command):
    def __init__(self):
        super(RunLegacyCommand, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'dry_run')
        parser.add_argument(
            'parameters', help='command to run', metavar='<command> [<argument>...]', nargs=argparse.REMAINDER
        )
        return True

    def is_available(self, env):
        return True, ''


class _Hook(RunLegacyCommand):
    '''Runs a hook'''

    def __init__(self):
        super(_Hook, self).__init__()

    def run(self, env):
        if len(env.parameters) != 0:
            logging.error('Too many arguments')
            return False
        return nimp.environment.execute_hook(env.hook, env)


class _Commandlet(RunLegacyCommand):
    '''Runs a commandlet'''

    def __init__(self):
        super(_Commandlet, self).__init__()

    def run(self, env):
        if not nimp.unreal.is_unreal_available(env):
            logging.error('Not an Unreal Engine project')
            return False

        return nimp.unreal.commandlet(env, env.parameters[0], *[env.format(arg) for arg in env.parameters[1:]])


class _Unreal_cli(RunLegacyCommand):
    '''Runs an unrel cli command'''

    def __init__(self):
        super(_Unreal_cli, self).__init__()

    def run(self, env):
        if not nimp.unreal.is_unreal_available(env):
            logging.error('Not an Unreal Engine project')
            return False
        return nimp.unreal.unreal_cli(env, *env.parameters)


class _Exec_cmds(RunLegacyCommand):
    '''Runs executables on the local host'''

    def __init__(self):
        super(_Exec_cmds, self).__init__()

    def run(self, env):
        cmdline = []
        for arg in env.parameters:
            cmdline.append(env.format(arg))

        nimp.environment.execute_hook('prerun', env)
        ret = nimp.sys.process.call(cmdline)
        nimp.environment.execute_hook('postrun', env)

        return ret == 0


class ConsoleGameCommand(RunLegacyCommand):
    def __init__(self, buildbot_directory_ending, local_directory):
        super(ConsoleGameCommand, self).__init__()
        self.buildbot_directory_ending = buildbot_directory_ending
        self.local_directory = local_directory

    def configure_arguments(self, env, parser):
        super(ConsoleGameCommand, self).configure_arguments(env, parser)
        nimp.utils.p4.add_arguments(parser)
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

        parser.add_argument(
            '--write-version',
            action="store_true",
            help='Will write a version.json file with package revision informations',
        )

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

    def run(self, env):
        self.platform_directory = nimp.sys.platform.create_platform_desc(env.platform).unreal_cook_name

        if env.fetch:
            if env.fetch.lower() == 'latest':
                env.fetch = self.get_latest_pgk_revision(env)

            return self.fetch(env)
        if env.deploy:
            return self.deploy(env)
        if env.launch:
            return self._launch(env)
        return False

    def fetch(self, env):
        package_revision = env.fetch
        env.fetch = self.get_path_from_parameter(env.fetch, env)
        if env.outdir == 'local':
            env.outdir = self.get_local_path(env)

        copy_cmd = self.fetch_with_robocopy if shutil.which('robocopy') else self.fetch_with_copy

        if not copy_cmd(env):
            return False

        if env.write_version:
            if not self.write_fetched_revision(env, package_revision):
                return False

        return True

    def write_fetched_revision(self, env, package_revision):
        if not str.isdigit(package_revision):
            logging.error('--write-revision is not compatible with package not from a CL')
            return False

        revision_info = {'dne_changelist': package_revision}

        p4 = nimp.utils.p4.get_client(env)

        # Retrieve P4 Stream root for this project because XPJ Monorepo streams are a thing
        output = p4._run('-Mj', 'fstat', '-m1', env.format("{uproject_dir}/..."), hide_output=True)
        lines = [json.loads(line) for line in output.splitlines(False)]
        if len(lines) != 1 or 'clientFile' not in lines[0] or 'depotFile' not in lines[0]:
            logging.error('Failed to find stream root')
            return False

        clientFile = lines[0]['clientFile']
        depotFile = lines[0]['depotFile']

        relClientFile = os.path.relpath(clientFile, os.path.abspath(env.root_dir))
        relClientFile = relClientFile.replace('\\', '/')
        if not depotFile.endswith(relClientFile):
            logging.error('depotFile does not match clientFile')
            return False

        depotRoot = depotFile[: -len(relClientFile)]

        output = p4._run('-Mj', 'print', f"{depotRoot}DNE/Build/Build.version@{package_revision}", hide_output=True)
        # Ignore first line which is file infos
        lines = []
        for raw_line in output.splitlines(keepends=False)[1:]:
            line: dict = json.loads(raw_line)
            data = line.pop('data', None)
            if data is not None and len(line) <= 0:
                lines.append(data)
        revision_info.update(json.loads(''.join(lines)))

        revision_filepath = os.path.join(env.outdir, 'Build.version')
        with open(revision_filepath, 'w') as fp:
            json.dump(revision_info, fp, indent=4)

        logging.info('Wrote revision file: %s', revision_filepath)

        return True

    def fetch_with_robocopy(self, env):
        logging.info('Mirroring ' + env.fetch + ' into ' + env.outdir)
        cmdline = ['robocopy', '/MIR', '/R:5', '/W:5', '/TBD', '/NJH', '/ETA', '/MT', '/J']
        if env.restartable_fetch:
            cmdline.append('/Z')
        cmdline += [env.fetch, env.outdir]
        logging.info('Running "%s"', cmdline)
        if env.dry_run:
            return True
        result = subprocess.call(
            cmdline
        )  # Call subprocess directly to allow "dynamic" output (with progress percentage)
        return result <= 1  # 0: nothing to copy. 1: some files were copied

    def fetch_with_copy(self, env):
        if os.path.exists(env.outdir):
            logging.warning(env.outdir + ' exists. Deleting it.')
            if not env.dry_run:
                shutil.rmtree(env.outdir)
        logging.info('Copying from ' + env.fetch + ' to ' + env.outdir)
        if env.dry_run:
            return True
        return shutil.copytree(env.fetch, env.outdir)

    def deploy(self, env):
        env.deploy = self.get_path_from_parameter(env.deploy, env)
        if not os.path.isdir(env.deploy):
            raise FileNotFoundError('Invalid path / could not find a valid pkg file in %s' % env.deploy)
        return self._deploy(env)

    def get_path_from_parameter(self, param, env):
        if str.isdigit(param):
            return self.fetch_pkg_by_revision(env, param)
        # if 'latest' was provided, fetch latest package uploaded to /b/
        elif param == 'local':
            return self.get_local_path(env)
        return param

    def get_local_path(self, env):
        path = env.uproject_dir + '/Saved/' + self.local_directory + '/' + self.platform_directory
        config_path = os.path.join(path, env.unreal_config)
        if os.path.exists(config_path):
            return config_path
        return path

    def fetch_pkg_by_revision(self, env, rev):
        if not env.variant:
            raise RuntimeError('"variant" parameter is required to fetch remote packages')

        logging.info('Looking for a %s test package at CL#%s' % (env.platform, rev))
        artifact_repository = env.format(env.artifact_repository_destination)
        deploy_repository = nimp.system.sanitize_path(
            artifact_repository
            + '/packages/'
            + env.variant
            + '/'
            + (
                '%s-%s-%s-%s-%s/%s/'
                % (env.project, env.variant, rev, env.platform, self.buildbot_directory_ending, self.platform_directory)
            )
        )
        return deploy_repository

    def get_latest_pgk_revision(self, env):
        if not env.variant:
            raise RuntimeError('"variant" parameter is required to fetch remote packages')

        artifact_repository = env.format(env.artifact_repository_destination)
        deploy_repository = nimp.system.sanitize_path(artifact_repository + '/packages/' + env.variant)
        logging.info('Looking for latest %s package in %s' % (env.platform, deploy_repository))

        rev = '0'
        regex = re.compile(
            ("%s-%s-" % (env.project, env.variant))
            + r'(\d+)'
            + ('-%s-%s' % (env.platform, self.buildbot_directory_ending))
        )
        for d in os.listdir(deploy_repository):
            m = regex.match(d)
            if m and m.group(1) > rev:
                rev = m.group(1)

        return rev

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
