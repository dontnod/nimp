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

''' Command to run executables or special commands '''

import abc
import argparse
import logging
import re
import os
import shutil
import subprocess

import nimp.command
import nimp.unreal
import nimp.sys.process
from nimp.sys.platform import create_platform_desc


class Run(nimp.command.CommandGroup):
    ''' Run executables, hooks, and commandlets '''

    def __init__(self):
        super(Run, self).__init__([_Hook(),
                                   _Commandlet(),
                                   _Exec_cmds(),
                                   _Staged(),
                                   _Package()])

    def is_available(self, env):
        return True, ''

class RunCommand(nimp.command.Command):
    def __init__(self):
        super(RunCommand, self).__init__()

    def configure_arguments(self, env, parser):
        parser.add_argument('parameters',
                            help='command to run',
                            metavar='<command> [<argument>...]',
                            nargs=argparse.REMAINDER)
        parser.add_argument('-n', '--dry-run',
                            action = 'store_true',
                            help = 'perform a test run, without writing changes')
        return True

    def is_available(self, env):
        return True, ''

class _Hook(RunCommand):
    ''' Runs a hook '''
    def __init__(self):
        super(_Hook, self).__init__()

    def run(self, env):
        if len(env.parameters) != 0:
            logging.error('Too many arguments')
            return False
        return nimp.environment.execute_hook(env.hook, env)

class _Commandlet(RunCommand):
    ''' Runs a commandlet '''

    def __init__(self):
        super(_Commandlet, self).__init__()

    def run(self, env):
        if not nimp.unreal.is_unreal_available(env):
            logging.error('Not an Unreal Engine project')
            return False
        return nimp.unreal.commandlet(env, env.parameters[0], *env.parameters[1:])

class _Exec_cmds(RunCommand):
    ''' Runs executables on the local host '''

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

class ConsoleGameCommand(RunCommand):
    def __init__(self, buildbot_directory_ending, local_directory):
        super(ConsoleGameCommand, self).__init__()
        self.buildbot_directory_ending = buildbot_directory_ending
        self.local_directory = local_directory

    def configure_arguments(self, env, parser):
        super(ConsoleGameCommand, self).configure_arguments(env, parser)
        nimp.command.add_common_arguments(parser, 'platform', 'configuration')

        parser.add_argument('--fetch',
                            metavar='<path | CL# | "latest">',
                            help='copies the game to the default location on this machine')
        parser.add_argument('--outdir',
                            nargs='?', default='local',
                            help='output directory for fetch')

        parser.add_argument('--deploy',
                            nargs='?', const='local',
                            metavar='<path | CL# | "latest">',
                            help="deploy the game to a devkit. If empty, deploys from the game's 'Saved' directory\
                                  WARNING: if passing a CL number or 'latest', be aware that\
                                  the game will be downloaded from B:\\, then reuploaded to the devkit!!\
                                  Avoid doing this over the VPN")

        parser.add_argument('--launch',
                            nargs='?', const='default',
                            metavar='<package_name>',
                            help='launch the game on a devkit')

        parser.add_argument('--device', metavar = '<host>', help = 'set target device')
        parser.add_argument('-v', '--variant', metavar="<variant_name>", help="name of variant")

    def run(self, env):
        if env.platform == 'win64':
            self.platform_directory = 'WindowsNoEditor'
        else:
            self.platform_directory = env.platform

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
            env.outdir = self.get_local_path(env)

        if shutil.which('robocopy'):
            return self.fetch_with_robocopy(env)
        else:
            return self.fetch_with_copy(env)

    def fetch_with_robocopy(self, env):
        logging.info('Mirroring ' + env.fetch + ' into ' + env.outdir)
        cmdline = [ 'robocopy', '/MIR', '/R:5', '/W:5', '/TBD', '/Z', '/NJH', '/ETA', '/MT', env.fetch, env.outdir ]
        logging.info('Running "%s"', ' '.join(cmdline))
        if env.dry_run:
            return True
        result = subprocess.call(cmdline) # Call subprocess directly to allow "dynamic" output (with progress percentage)
        return result <= 1 # 0: nothing to copy. 1: some files were copied
    
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
        elif param.lower() == 'latest':
            return self.fetch_pkg_latest(env)
        elif param == 'local':
            return self.get_local_path(env)
        return param

    def get_local_path(self, env):
        return env.uproject_dir + '/Saved/' + self.local_directory + '/' + self.platform_directory

    def fetch_pkg_by_revision(self, env, rev):
        if not env.variant:
            raise RuntimeError('"variant" parameter is required to fetch remote packages')

        logging.info('Looking for a %s test package at CL#%s' % (env.platform, rev))
        artifact_repository = env.format(env.artifact_repository_destination)
        deploy_repository =  nimp.system.sanitize_path(artifact_repository + '/packages/' + env.variant + '/' +
                                    ('%s-%s-%s-%s-%s/%s/' % (env.project, env.variant, rev, env.platform, self.buildbot_directory_ending, self.platform_directory)))
        return deploy_repository

    def fetch_pkg_latest(self, env):
        if not env.variant:
            raise RuntimeError('"variant" parameter is required to fetch remote packages')

        artifact_repository = env.format(env.artifact_repository_destination)
        deploy_repository =  nimp.system.sanitize_path(artifact_repository + '/packages/' + env.variant)
        logging.info('Looking for latest %s package in %s' % (env.platform, deploy_repository))

        rev = '0'
        regex = re.compile(("%s-%s-" % (env.project, env.variant)) + r'(\d+)' + ('-%s-%s' % (env.platform, self.buildbot_directory_ending)))
        for d in os.listdir(deploy_repository):
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
    ''' Deploys and runs staged console builds '''

    def __init__(self):
        super(_Staged, self).__init__('staged', 'StagedBuilds')

    def _deploy(self, env):
        # ./RunUAT.sh BuildCookRun -project=ALF -platform=xsx -skipcook -skipstage -deploy [-configuration=Development] [-device=IP]

        absolute_path = os.path.abspath(env.deploy + '/..') # UAT expects this to point to StagedBuilds directory, not StagedBuilds/Platform

        cmdline = [
            env.unreal_dir + '/Engine/Binaries/DotNet/AutomationTool.exe',
            'BuildCookRun', '-project=' + env.game, '-platform=' + env.platform, '-configuration=' + env.ue4_config,
            '-stagingdirectory=' + absolute_path, 
            '-skipcook', '-skipstage', '-deploy'
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
        absolute_path = os.path.abspath(env.launch + '/..') # UAT expects this to point to StagedBuilds directory, not StagedBuilds/Platform

        cmdline = [
            env.unreal_dir + '/Engine/Binaries/DotNet/AutomationTool.exe',
            'BuildCookRun', '-project=' + env.game, '-platform=' + env.platform, '-configuration=' + env.ue4_config,
            '-stagingdirectory=' + absolute_path,
            '-skipcook', '-skipstage', '-deploy', '-run'
        ]
        if env.device:
            cmdline.append('-device=' + env.device)

        result = nimp.sys.process.call(cmdline, dry_run=env.dry_run)
        return result == 0

class _Package(ConsoleGameCommand):
    ''' Deploys and runs console packages '''

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