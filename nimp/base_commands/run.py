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
        if not nimp.unreal.is_unreal4_available(env):
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
    def __init__(self):
        super(ConsoleGameCommand, self).__init__()

    def configure_arguments(self, env, parser):
        super(ConsoleGameCommand, self).configure_arguments(env, parser)
        nimp.command.add_common_arguments(parser, 'platform')
        parser.add_argument('--deploy', action='store_true', help='deploy the game to a devkit')
        parser.add_argument('--launch', action='store_true', help='launch the game on a devkit')
        parser.add_argument('--device', metavar = '<host>', help = 'set target device')
        parser.add_argument('--package_name', help = 'name of the package to launch')

    def run(self, env):
        if env.deploy:
            return self._deploy(env)
        if env.launch:
            return self._launch(env)
        return False

    @abc.abstractmethod
    def _deploy(self, env):
        pass

    @abc.abstractmethod
    def _launch(self, env):
        pass

class _Staged(ConsoleGameCommand):
    ''' Deploys and runs staged console builds '''

    def __init__(self):
        super(_Staged, self).__init__()

    def _deploy(self, env):
        # ./RunUAT.sh BuildCookRun -project=ALF -platform=xsx -skipcook -skipstage -deploy [-configuration=Development] [-device=IP]
        return True

    def _launch(self, env):
        # ./RunUAT.sh BuildCookRun -project=ALF -platform=xsx -skipcook -skipstage -deploy -run [-device=IP]
        return True

class _Package(ConsoleGameCommand):
    ''' Deploys and runs console packages '''

    def __init__(self):
        super(_Package, self).__init__()

    def _deploy(self, env):
        platform_desc = create_platform_desc(env.platform)
        package_directory = env.format('{uproject_dir}/Saved/Packages/{platform}')
        platform_desc.install_package(package_directory, env.device, env.dry_run)
        return True

    def _launch(self, env):
        platform_desc = create_platform_desc(env.platform)
        package_name = env.package_name
        if not package_name:
            package_name = env.game
        platform_desc.launch_package(package_name, env.device, env.dry_run)
        return True