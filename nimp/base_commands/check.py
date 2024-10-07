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
from typing import Sequence

import psutil

import nimp.command
import nimp.sys.platform
import nimp.sys.process
from nimp.environment import Environment as NimpEnvironment


class Check(nimp.command.CommandGroup):
    '''Check related commands'''

    def __init__(self):
        super(Check, self).__init__([_Status(), _Processes(), _Disks()])

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
    PROCESS_IGNORE_PATTERNS: Sequence[re.Pattern] = (
        # re.compile(r'^CrashReportClient\.exe$', re.IGNORECASE),
        re.compile(r'^dotnet\.exe$', re.IGNORECASE),
    )

    def configure_arguments(self, env, parser):
        parser.add_argument('-k', '--kill', help='Kill processes that can prevent builds', action='store_true')
        parser.add_argument(
            '-f',
            '--filters',
            nargs='*',
            help='fnmatch filters, defaults to workspace',
            default=[os.path.normpath(f'{os.path.abspath(env.root_dir)}/*')],
        )
        parser.add_argument(
            '--all-users',
            help='By default, only check processes owned by the current user. Use this to check all running processes.',
            action='store_true',
        )
        return True

    def _run_check(self, env: NimpEnvironment):
        logging.info('Checking running processes…')
        logging.debug('\tUsing filters: %s', env.filters)

        # Irrelevant on sane Unix platforms
        if not nimp.sys.platform.is_windows():
            logging.warning("Command only available on Windows platform")
            return True

        current_user: str | None = None
        if not env.all_users:
            current_user = psutil.Process().username()
            logging.debug("Only act on processes owned by %s", current_user)

        # Find all running processes running a program that any filter match either:
        #  - the program executable
        #  - an open file handle
        # and optionally kill them, unless they’re in the exception list.
        # We get to try 5 times just in case
        for _ in range(5):
            checked_processes_count = 0
            problematic_processes: list[psutil.Process] = []

            # psutil.process_iter caches processes
            # we want a fresh list since we might have killed/
            # process completed since last iteration
            logging.debug("Clear psutil process cache")
            psutil.process_iter.cache_clear()
            logging.debug("Get current process")
            current_process = psutil.Process()
            logging.debug("Current process is %d", current_process.pid)
            ignore_process_ids = set(
                (
                    current_process.pid,
                    *(p.pid for p in current_process.parents()),
                    *(p.pid for p in current_process.children(recursive=True)),
                )
            )
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                logging.debug("Ignore processes:")
                for pid in ignore_process_ids:
                    ignored_process = psutil.Process(pid)
                    logging.debug("\t%s (%s) %s", ignored_process.exe(), ignored_process.pid, ignored_process.cmdline())

            for process in psutil.process_iter():
                logging.debug("Checking process %d", process.pid)
                if process.pid in ignore_process_ids:
                    logging.debug("[Process(%d)] ignore process (self, parent or child)", process.pid)
                    continue

                if current_user is not None:
                    process_user = None
                    try:
                        process_user = process.username()
                    except psutil.AccessDenied:
                        logging.debug(
                            "[Process(%d)] Failed to retrieve process user",
                            process.pid,
                        )
                        continue

                    if current_user != process_user:
                        logging.debug(
                            "[Process(%d)] ignore process from other user (self: %s, process user: %s)",
                            process.pid,
                            current_user,
                            process_user,
                        )
                        continue

                checked_processes_count += 1
                if not _Processes._process_matches_filters(process, env.filters):
                    continue

                process_executable_path = process.exe()
                process_basename = os.path.basename(process_executable_path)
                if any(p.match(process_basename) for p in _Processes.PROCESS_IGNORE_PATTERNS):
                    logging.info('[Process(%d)] process (%s) will be kept alive', process.pid, process_executable_path)
                    continue

                problematic_processes.append(process)
                logging.warning('[Process(%d)] Found problematic process (%s)', process.pid, process_executable_path)
                if (parent_process := process.parent()) is not None:
                    logging.warning('\tParent is %s (%s)', parent_process.pid, parent_process.exe())

            logging.info('%d processes checked.', checked_processes_count)
            if not problematic_processes:
                # no problematic processes running, nothing to do.
                return True

            if not env.kill:
                # Wait a bit, give a chance to problematic processes to end,
                # even if not killed
                sleep_time = 5.0
                logging.debug("Wait %.2fs. Giving a chance to processes for a natural exit", sleep_time)
                time.sleep(sleep_time)
            else:
                for p in problematic_processes:
                    logging.info('Requesting process %s termination', p.pid)
                    p.terminate()
                _, alive = psutil.wait_procs(problematic_processes, timeout=5)
                for p in alive:
                    logging.info('Process %s not terminated. Send kill.', p.pid)
                    p.kill()

        return False

    @staticmethod
    def _process_matches_filters(process: psutil.Process, filters: list[str]) -> bool:
        """Returns True if the process should be filtered out"""
        try:
            logging.debug("[Process(%d)] Check process against filters", process.pid)
            for idx, pattern in enumerate(filters, start=1):
                logging.debug("[Process(%d)] Filter: %s (%02d/%02d)", process.pid, pattern, idx, len(filters))
                logging.debug("[Process(%d)]\tmatch exe '%s'?", process.pid, process.exe())
                if fnmatch.fnmatch(process.exe(), pattern):
                    logging.debug(
                        "process %s (%s), match filter '%s' with exe '%s'",
                        process.pid,
                        process.exe(),
                        pattern,
                        process.exe(),
                    )
                    return True

                logging.debug("[Process(%d)]\tmatch open files?", process.pid)
                for popen_file in process.open_files():
                    logging.debug("[Process(%d)]\t\tfilepath: %s", process.pid, popen_file.path)
                    if fnmatch.fnmatch(popen_file.path, pattern):
                        logging.debug(
                            "process %s (%s), match filter '%s' with popen file '%s'",
                            process.pid,
                            process.exe(),
                            pattern,
                            popen_file.path,
                        )
                        return True
        except psutil.AccessDenied as exc:
            logging.debug("[Process(%d)] Access Denied!", process.pid, exc_info=exc)
            # failed to access a property of the process,
            # assume it does not match to be safe
            return False

        return False


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
