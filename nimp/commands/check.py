# -*- coding: utf-8 -*-

import sys
import platform
import os
import unittest

from nimp.commands.command import *

from nimp.tests.utilities import file_mapper_tests
from nimp.utilities.system import *


class CheckCommand(Command):

    def __init__(self):
        Command.__init__(self, 'check', 'Various checks about the environment')


    def configure_arguments(self, env, parser):

        parser.add_argument('mode',
                            help = 'Check mode (status, nimp, processes)',
                            metavar = '<mode>')

        return True


    def run(self, env):

        # Check running processes for possible issues
        if env.mode == 'processes':
            return self.check_processes(env)

        # Print information about the current environment
        if env.mode == 'status':
            self.info_project(env)
            self.info_python(env)
            self.info_env(env)
            return True;

        # Check nimp itself using pylint and run the unit tests
        if env.mode == 'nimp':
            return unittest.main(module = file_mapper_tests, argv = ["."])

        log_error('Unsupported check mode “{0}”', env.mode)
        return False


    def check_processes(self, env):

        log_verbose('Checking running processes…')

        # Irrelevant on sane Unix platforms
        if not is_windows():
            return True

        # Irrelevant if we’re not a UE3 or UE4 project
        if not hasattr(env, 'project_type'):
            return True

        if env.project_type not in [ 'UE3', 'UE4' ]:
            return True

        # List all processes
        cmd = ['wmic', 'process', 'get', 'executablepath,parentprocessid,processid', '/value']
        result, output, error = capture_process_output('.', cmd)
        if result != 0:
            return False

        # Build a dictionary of all processes
        processes = {}
        path, pid, ppid = '', 0, 0
        for l in [l.strip() for l in output.splitlines()]:
            if l.lower().startswith('executablepath='):
                path = re.sub('[^=]*=', '', l)
            if l.lower().startswith('parentprocessid='):
                ppid = re.sub('[^=]*=', '', l)
            if l.lower().startswith('processid='):
                pid = re.sub('[^=]*=', '', l)
                processes[pid] = (path, ppid)

        # Find all running binaries launched from the project directory and kill them
        prefix = os.path.abspath(env.root_dir).replace('/', '\\').lower()
        for pid, info in processes.items():
            if info[0].lower().startswith(prefix):
                log_warning('Found problematic process {0} ({1})', pid, info[0])
                if info[1] in processes:
                    log_warning('Parent is {0} ({1})', info[1], processes[info[1]][0])
                log_warning('Killing process…')
                call_process('.', ['wmic', 'process', 'where', 'processid=' + pid, 'delete'])

        log_verbose('{0} processes checked.', len(processes))

        return True


    def info_project(self, env):
        print('Project:')
        if hasattr(env, 'game'): print('  game: ', env.game)
        if hasattr(env, 'project'): print('  project name: ', env.project)
        if hasattr(env, 'project_type'): print('  project type: ', env.project_type)
        if hasattr(env, 'root_dir'): print('  root directory: ', os.path.abspath(env.root_dir))
        print()


    def info_python(self, env):
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


    def info_env(self, env):
        print('Environment:')
        for key, val in sorted(os.environ.items()):
            print('  ' + key + '=' + val)
        print()

