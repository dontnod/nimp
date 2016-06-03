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
''' Command to wrap command execution '''

import nimp.command
import nimp.system

class Run(nimp.command.Command):
    ''' Simply runs a command '''
    def __init__(self):
        super(Run, self).__init__()

    def configure_arguments(self, env, parser):
        parser.add_argument('command_and_args',
                            help     = 'Command to run',
                            nargs    = '+',
                            metavar  = '<command> [<argument>...]')
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        cmdline = []
        for arg in env.command_and_args:
            cmdline.append(env.format(arg))

        return nimp.system.call_process(".", cmdline) == 0
