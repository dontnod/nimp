# -*- coding: utf-8 -*-
# Copyright (c) 2014-2023 Dontnod Entertainment

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

'''System utilities unit tests'''

import os

import unittest.mock
from contextlib import contextmanager

from functools import wraps
import nimp.tests.utils
import nimp.nimp_cli


def test_decorator(f):
    """Decorator to print test function name"""

    @wraps(f)
    def wrapper(*args, **kwds):
        print(f'\n****** UNIT TEST : {f.__name__} ******')
        return f(*args, **kwds)

    return wrapper


@contextmanager
def cwd(path):
    oldpwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(oldpwd)


class _UnrealTests(unittest.TestCase):
    '''
    Environment variables needed:
        - TEST_GAME_CODE
        - TEST_WORKSPACE_DIR
        - P4PORT [optional]
        - P4USER [optional]
        - P4CLIENT [optional]
    '''

    GAME_CODE = os.getenv('TEST_GAME_CODE')
    WORKSPACE_DIR = os.getenv('TEST_WORKSPACE_DIR')
    WORKSPACE_BRANCH = os.getenv('TEST_WORKSPACE_BRANCH', 'main')
    assert GAME_CODE is not None
    assert WORKSPACE_DIR is not None

    GAME_PATH = '%s/%s' % (WORKSPACE_DIR, GAME_CODE)
    P4_PORT = os.getenv('P4PORT')
    P4_USER = os.getenv('P4USER')
    P4_CLIENT = os.getenv('P4CLIENT')

    def _get_common_nimp_cmd(self, is_dry_run=True):
        cmd_nimp = [
            'nimp',
            '-v',
            '--uproject',
            f'{self.GAME_CODE}/{self.GAME_CODE}.UPROJECT',
            '--branch',
            self.WORKSPACE_BRANCH,
            'run',
            'commandlet',
        ]
        if is_dry_run:
            cmd_nimp.append('--dry-run')
        return cmd_nimp

    def _get_common_p4(self):
        return [
            '-SCCProvider=Perforce',
            f'-P4Port={self.P4_PORT}',
            f'-P4Port={self.P4_USER}',
            f'-P4Client={self.P4_CLIENT}',
        ]

    @test_decorator
    def test_loadpackage(self):
        cmd_to_test = self._get_common_nimp_cmd(is_dry_run=False) + [
            '--',
            'loadpackage',
            '-crashreports',
            '-skipmaps',
            '-nodev',
            '-notiled',
            '-fast',
            '-projectonly',
            '-nopreprod',
            '*Layout*.uasset',
        ]
        with cwd(self.GAME_PATH):
            self.assertEqual(0, nimp.nimp_cli.main(cmd_to_test))
