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

import nimp.command
import nimp.system

class Check(nimp.command.Command):
    ''' Performs various checks on the environment '''
    def __init__(self):
        super(Check, self).__init__()


    def configure_arguments(self, env, parser):
        parser.add_argument('mode',
                            help = 'Check mode (status, nimp, processes)',
                            metavar = '<mode>',
                            choices = ['status', 'processes', 'disk'])

        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        # Check running processes for issues and kill them if necessary
        if env.mode == 'processes':
            return Check._check_processes(env)

        # Check disk space and block until there is free space
        if env.mode == 'disk':
            return Check._check_disk(env.root_dir)

        # Print information about the current environment
        if env.mode == 'status':
            Check._info_project(env)
            Check._info_python()
            Check._info_env()
            return True

        return False

    @staticmethod
    def _check_processes(env):
        logging.debug('Checking running processes…')

        # Irrelevant on sane Unix platforms
        if not nimp.system.is_windows():
            return True

        # Irrelevant if we’re not a UE3 or UE4 project
        if not hasattr(env, 'project_type'):
            return True

        if env.project_type not in [ 'UE3', 'UE4' ]:
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

        # Find all running binaries launched from the project directory and kill them
        prefix = os.path.abspath(env.root_dir).replace('/', '\\').lower()
        for pid, info in processes.items():
            if info[0].lower().startswith(prefix):
                logging.warning('Found problematic process %s (%s)', pid, info[0])
                if info[1] in processes:
                    logging.warning('Parent is %s (%s)', info[1], processes[info[1]][0])
                logging.warning('Killing process…')
                nimp.system.call_process('.', ['wmic', 'process', 'where', 'processid=' + pid, 'delete'])

        logging.debug('%s processes checked.', len(processes))

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

    @staticmethod
    def _check_disk(path):
        # Check every 5 minutes, for a maximum of 2 hours
        wait_time = 5 * 60
        total_wait_time = 2 * 60 * 60
        byte2gib = 1.0 / 1024 / 1024 / 1024
        while total_wait_time > 0:
            total, used, free = shutil.disk_usage(path)
            logging.warning('Disk usage: %.2f GiB total, %.2f GiB used, %.2f GiB free',
                            total * byte2gib, used * byte2gib, free * byte2gib)
            free_percent = 100.0 * free / total
            if free_percent > 0.5:
                return True
            logging.warning('Only %f%% free on disk, waiting for %d seconds',
                            free_percent, wait_time)
            time.sleep(wait_time)
            total_wait_time -= wait_time
        return False

