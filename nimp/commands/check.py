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
''' Environment check command '''

import logging
import os
import platform
import re
import shutil
import time
import abc

import nimp.command
import nimp.system

class Check(nimp.command.CommandGroup):
    ''' Check related commands '''
    def __init__(self):
        super(Check, self).__init__([_Status(),
                                     _Processes(),
                                     _Disks()])
    def is_available(self, env):
        return True, ''


class CheckCommand(nimp.command.Command):
    ''' Performs various checks on the local host '''
    def __init__(self):
        super(CheckCommand, self).__init__()

    def configure_arguments(self, env, parser):
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        return self._run_check(env)

    @abc.abstractmethod
    def _run_check(self,env):
        pass


class _Status(CheckCommand):
    def __init__(self):
        super(_Status, self).__init__()

    def _run_check(self, env):
        _Status._info_project(env)
        _Status._info_python()
        _Status._info_env()
        return True

    @staticmethod
    def _info_project(env):
        print('Project:')
        if hasattr(env, 'game'):
            print('  game: ', env.game)
        if hasattr(env, 'project'):
            print('  project name: ', env.project)
        if hasattr(env, 'project_type'):
            print('  project type: ', env.project_type)
        if hasattr(env, 'root_dir'):
            print('  root directory: ', os.path.abspath(env.root_dir))
        print()

    @staticmethod
    def _info_python():
        print('Python:')
        print('  runtime version: ', platform.python_version())
        print(('  system:  %s\n' +
               '  node:  %s\n' +
               '  release:  %s\n' +
               '  version:  %s\n' +
               '  machine:  %s\n' +
               '  processor:  %s')
              % platform.uname())
        print('  directory separator: ', os.sep)
        print('  path separator: ', os.pathsep)
        print('')

    @staticmethod
    def _info_env():
        print('Environment:')
        for key, val in sorted(os.environ.items()):
            print('  ' + key + '=' + val)
        print()


class _Processes(CheckCommand):
    def __init__(self):
        super(_Processes, self).__init__()

    def configure_arguments(self, env, parser):
        parser.add_argument('-k', '--kill',
                            help = 'Kill processes that can prevent builds',
                            default = False, action = 'store_true')
        return True

    def _run_check(self, env):
        logging.info('Checking running processes…')

        # Irrelevant on sane Unix platforms
        if not nimp.system.is_windows():
            return True

        # Irrelevant if we’re not a UE4 project
        if not hasattr(env, 'project_type') or env.project_type not in [ 'UE4' ]:
            return True

        # List all processes
        cmd = ['wmic', 'process', 'get', 'executablepath,parentprocessid,processid', '/value']
        result, output, _ = nimp.system.capture_process_output('.', cmd)
        if result != 0:
            return False

        # Build a dictionary of all processes
        processes = {}
        path, pid, ppid = '', 0, 0
        for line in [line.strip() for line in output.splitlines()]:
            if line.lower().startswith('executablepath='):
                path = re.sub('[^=]*=', '', line)
            if line.lower().startswith('parentprocessid='):
                ppid = re.sub('[^=]*=', '', line)
            if line.lower().startswith('processid='):
                pid = re.sub('[^=]*=', '', line)
                processes[pid] = (path, ppid)

        success = True

        # Find all running binaries launched from the project directory and kill them
        prefix = os.path.abspath(env.root_dir).replace('/', '\\').lower()
        for pid, info in processes.items():
            if info[0].lower().startswith(prefix):
                logging.warning('Found problematic process %s (%s)', pid, info[0])
                if info[1] in processes:
                    logging.warning('Parent is %s (%s)', info[1], processes[info[1]][0])
                if env.kill:
                    logging.info('Killing process…')
                    nimp.system.call_process('.', ['wmic', 'process', 'where', 'processid=' + pid, 'delete'])
                else:
                    success = False

        logging.info('%s processes checked.', len(processes))

        return success


class _Disks(CheckCommand):
    def __init__(self):
        super(_Disks, self).__init__()

    def configure_arguments(self, env, parser):
        parser.add_argument('-w', '--warning',
                            help = 'emit warnings when free space is below threshold (default 5.0)',
                            metavar = '<percent>', type = float, default = 5.0)
        parser.add_argument('-e', '--error',
                            help = 'error out when free space is below threshold (default 1.0)',
                            metavar = '<percent>', type = float, default = 1.0)
        parser.add_argument('-d', '--delay',
                            help = 'wait X seconds before exiting with error (default 10)',
                            metavar = 'X', type = int, default = 10)
        return True

    def _run_check(self, env):
        path = env.root_dir
        wait_time = min(env.delay, 5 * 60) # Check at least every 5 minutes
        total_wait_time = env.delay

        while True:
            total, used, free = shutil.disk_usage(path)
            byte2gib = 1.0 / 1024 / 1024 / 1024
            byte2pct = 100.0 / total
            logging.info('Disk usage: %.2f GiB total, %.2f GiB used (%.2f%%), %.2f GiB free (%.2f%%)',
                         total * byte2gib, used * byte2gib, used * byte2pct, free * byte2gib, free * byte2pct)
            free_percent = free * byte2pct
            if free_percent < env.error:
                if total_wait_time <= 0:
                    return False
                logging.warning('Only %.2f%% free on disk, waiting for %d seconds',
                                free_percent, wait_time)
            else:
                if free_percent < env.warning:
                    logging.warning('Only %.2f%% free space on disk', free_percent)
                break
            time.sleep(wait_time)
            total_wait_time -= wait_time
        return True

