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
''' System utilities unit tests '''

import abc
import contextlib
import os.path
import unittest.mock

import pyfakefs.fake_filesystem_unittest

import nimp.system

class MockCommand(metaclass=abc.ABCMeta):
    ''' Used to mock a call to a system command '''
    def __init__(self, command):
        self.command = command

    @abc.abstractmethod
    def get_result(self, command, stdin = None):
        ''' Returns a tuple containing return code, stdout and stderr when
            calling command '''

@contextlib.contextmanager
def mock_capture_process_output(*mock_commands):
    ''' Mocks calls to popen '''
    mock_dict = {}
    for it in mock_commands:
        assert isinstance(it, MockCommand)
        mock_dict[it.command] = it

    def _mock(directory, command, stdin = None, _ = True):
        assert directory is not None
        executable = command[0]
        assert executable in mock_dict
        return mock_dict[executable].get_result(command[1:], stdin = stdin)

    with unittest.mock.patch('nimp.system.capture_process_output') as mock:
        with unittest.mock.patch('nimp.system.is_msys') as mock_is_msys:
            mock_is_msys.return_value = False
            mock.side_effect = _mock
            yield mock

@contextlib.contextmanager
def mock_filesystem():
    ''' Sets up a mock filesystem '''
    patcher = pyfakefs.fake_filesystem_unittest.Patcher()
    patcher.setUp()
    yield patcher.fs
    patcher.tearDown()

def create_file( name, content):
    ''' Creates a file on the fake file system '''
    dirname = os.path.dirname(name)
    nimp.system.safe_makedirs(dirname)
    with open(name, 'w') as file_content:
        file_content.write(content)

