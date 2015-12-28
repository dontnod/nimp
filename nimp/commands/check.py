# -*- coding: utf-8 -*-

import sys
import platform
import os
import unittest

from nimp.commands._command import *

from nimp.tests.utilities import file_mapper_tests
from nimp.utilities.processes import *


class CheckCommand(Command):

    def __init__(self):
        Command.__init__(self, 'check', 'Various checks about the environment')


    def configure_arguments(self, env, parser):

        parser.add_argument('mode',
                            help = 'Check mode (status, nimp)',
                            metavar = '<mode>')

        return True


    def run(self, env):

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

