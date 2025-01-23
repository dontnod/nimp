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

'''Environment check command'''

from __future__ import annotations

import abc
import fnmatch
import json
import logging
import os
import platform
import re
import shutil
import time


import nimp.command
import nimp.sys.platform
import nimp.sys.process
from nimp.environment import Environment as NimpEnvironment


class Check(nimp.command.CommandGroup):
    '''Check related commands'''

    def __init__(self):
        super(Check, self).__init__(
            [
                _Status(),
                _Processes(),
                _Disks(),
            ]
        )

    def is_available(self, env):
        return True, ''


class CheckCommand(nimp.command.Command):
    '''Performs various checks on the local host'''

    def __init__(self):
        super(CheckCommand, self).__init__()

    def configure_arguments(self, env, parser):
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        return self._run_check(env)

    @abc.abstractmethod
    def _run_check(self, env):
        pass


class _Status(CheckCommand):
    def __init__(self):
        super(_Status, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'free_parameters')
        return True

    def _run_check(self, env):
        print()
        _Status._show_project_information(env)
        _Status._show_system_information()
        _Status._show_user_environment()
        _Status._show_nimp_environment(env)
        nimp.environment.execute_hook('status', env)
        return True

    @staticmethod
    def _show_project_information(env):
        print('Project:')
        if hasattr(env, 'game'):
            print('  game: %s' % env.game)
        if hasattr(env, 'project'):
            print('  project name: %s' % env.project)
        if hasattr(env, 'root_dir'):
            print('  root directory: %s' % os.path.abspath(env.root_dir))
        print()

    @staticmethod
    def _show_system_information():
        print('System:')
        print('  computer: %s' % platform.node())
        print('  operating system: %s' % platform.platform())
        print('  processor: %s' % platform.processor())
        print('  python version: %s' % platform.python_version())
        print('  directory separator: %s' % os.sep)
        print('  path separator: %s' % os.pathsep)
        print()

    @staticmethod
    def _json_serialize(o):
        if isinstance(o, nimp.command.Command):
            return f'<command {o.__class__.__name__}>'
        if isinstance(o, nimp.sys.platform.Platform):
            return f'<platform {o.__name__}>'
        return o.__dict__

    @staticmethod
    def _show_user_environment():
        print(
            'User Environment: %s'
            % json.dumps(dict(os.environ), default=_Status._json_serialize, indent=2, sort_keys=True)
        )
        print()

    @staticmethod
    def _show_nimp_environment(env):
        print('Nimp Environment: %s' % json.dumps(env, default=_Status._json_serialize, indent=2, sort_keys=True))
        print()


class _Processes(CheckCommand):
    def configure_arguments(self, env, parser):
        parser.add_argument('-k', '--kill', help='Kill processes that can prevent builds', action='store_true')
        parser.add_argument(
            '-f',
            '--filters',
            nargs='*',
            help='fnmatch filters, defaults to workspace',
            default=[os.path.normpath(f'{os.path.abspath(env.root_dir)}/*')],
        )
        return True

    def _run_check(self, env: NimpEnvironment):
        logging.info('Checking running processes…')
        logging.debug('\tUsing filters: %s', env.filters)

        # Irrelevant on sane Unix platforms
        if not nimp.sys.platform.is_windows():
            logging.warning("Command only available on Windows platform")
            return True

        # Find all running binaries launched from the project directory
        # and optionally kill them, unless they’re in the exception list.
        # We get to try 5 times just in case
        for _ in range(5):
            found_problem = False
            processes = _Processes._list_windows_processes()

            for pid, info in processes.items():
                if not any(fnmatch.fnmatch(info[0], filter) for filter in env.filters):
                    continue
                process_basename = os.path.basename(info[0])
                processes_ignore_patterns = _Processes.get_processes_ignore_patterns()
                if any([re.match(p, process_basename, re.IGNORECASE) for p in processes_ignore_patterns]):
                    logging.info(f'process {pid} {info[0]} will be kept alive')
                    continue
                logging.warning('Found problematic process %s (%s)', pid, info[0])
                found_problem = True
                if info[1] in processes:
                    logging.warning('Parent is %s (%s)', info[1], processes[info[1]][0])
                if env.kill:
                    logging.info('Killing process…')
                    nimp.sys.process.call(['wmic', 'process', 'where', 'processid=' + pid, 'delete'])
            logging.info('%s processes checked.', len(processes))
            if not env.kill:
                return not found_problem
            if not found_problem:
                return True
            time.sleep(5)

        return False

    @staticmethod
    def get_processes_ignore_patterns():
        return [
            # r'^CrashReportClient\.exe$',
            r'^dotnet\.exe$',
        ]

    @staticmethod
    def _list_windows_processes():
        processes = {}
        # List all processes
        cmd = ['wmic', 'process', 'get', 'executablepath,parentprocessid,processid', '/value']
        result, output, _ = nimp.sys.process.call(cmd, capture_output=True)
        if result == 0:
            # Build a dictionary of all processes
            path, pid, ppid = '', 0, 0
            for line in [line.strip() for line in output.splitlines()]:
                if line.lower().startswith('executablepath='):
                    path = re.sub('[^=]*=', '', line)
                if line.lower().startswith('parentprocessid='):
                    ppid = re.sub('[^=]*=', '', line)
                if line.lower().startswith('processid='):
                    pid = re.sub('[^=]*=', '', line)
                    processes[pid] = (path, ppid)
        return processes


class _Disks(CheckCommand):
    def __init__(self):
        super(_Disks, self).__init__()

    def configure_arguments(self, env, parser):
        parser.add_argument(
            '-w',
            '--warning',
            help='emit warnings when free space is below threshold (default 5.0)',
            metavar='<percent>',
            type=float,
            default=5.0,
        )
        parser.add_argument(
            '-e',
            '--error',
            help='error out when free space is below threshold (default 1.0)',
            metavar='<percent>',
            type=float,
            default=1.0,
        )
        parser.add_argument(
            '-d',
            '--delay',
            help='wait X seconds before exiting with error (default 10)',
            metavar='X',
            type=int,
            default=10,
        )
        return True

    def _run_check(self, env):
        path = env.root_dir
        wait_time = min(env.delay, 5 * 60)  # Check at least every 5 minutes
        total_wait_time = env.delay

        ran_callback = False
        while True:
            total, used, free = shutil.disk_usage(path)
            byte2gib = 1.0 / 1024 / 1024 / 1024
            byte2pct = 100.0 / total
            logging.info(
                'Disk usage on %s: %.2f GiB total, %.2f GiB used (%.2f%%), %.2f GiB free (%.2f%%)',
                path,
                total * byte2gib,
                used * byte2gib,
                used * byte2pct,
                free * byte2gib,
                free * byte2pct,
            )
            free_percent = free * byte2pct
            if not ran_callback and free_percent < env.warning:
                logging.warning('Only %.2f%% free space on disk, trying diskfull hook', free_percent)
                nimp.environment.execute_hook('diskfull', env)
                ran_callback = True
                continue
            if free_percent >= env.warning:
                break
            if free_percent >= env.error:
                logging.warning('Only %.2f%% free space on disk', free_percent)
                break
            if total_wait_time <= 0:
                return False
            logging.warning('Only %.2f%% free on disk, waiting for %d seconds', free_percent, wait_time)
            time.sleep(wait_time)
            total_wait_time -= wait_time
        return True
