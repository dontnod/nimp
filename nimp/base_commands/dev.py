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

'''Dev & Testing related commands'''

import logging

import nimp.command


class Dev(nimp.command.CommandGroup):
    '''Dev and test related commands.'''

    def __init__(self):
        super(Dev, self).__init__([_TestLogPatterns()])

    def configure_arguments(self, env, parser):
        super(Dev, self).configure_arguments(env, parser)

    def is_available(self, env):
        return True, ''


class _TestLogPatterns(nimp.command.Command):
    '''Reads a file and outputs it to test logging patterns.'''

    def __init__(self):
        super(_TestLogPatterns, self).__init__()

    def is_available(self, env):
        return True, ''

    def configure_arguments(self, env, parser):
        # These are not marked required=True because sometimes we don’t
        # really need them.
        super(_TestLogPatterns, self).configure_arguments(env, parser)

        parser.add_argument('input_file', help='The file to pass through logging system')

        return True

    def run(self, env):
        logger = logging.getLogger('child_processes')
        with open(env.input_file) as file:
            for line in file:
                line = line[:-1]
                logger.info(line)
        return True
