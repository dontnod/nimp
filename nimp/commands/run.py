# -*- coding: utf-8 -*-
# Copyright (c) 2016 Dontnod Entertainment

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
''' Command for building '''

import sys
import argparse

import nimp.command

class _RunCommand(nimp.command.Command):
    def __init__(self):
        super(_RunCommand, self).__init__('run', 'Executes a shell command')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('command',
                            help     = 'Command to run',
                            nargs    = argparse.REMAINDER,
                            metavar  = '<COMMAND> [<ARGUMENT>...]')
        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        cmdline = []
        for arg in env.command:
            cmdline.append(env.format(arg))

        return call_process(".", cmdline,
                            stdout_callback = _stdout_callback,
                            stderr_callback = _stderr_callback) == 0

def _stdout_callback(line, default_log_function):
    print(line, file = sys.stdout)

def _stderr_callback(line, default_log_function):
    print(line, file = sys.stderr)

