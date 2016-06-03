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
''' Unreal Engine commandlet execution command '''

import argparse

import nimp.command
import nimp.unreal

class Commandlet(nimp.command.Command):
    ''' Runs an Unreal Engine Commandlet. '''
    def __init__(self):
        super(Commandlet, self).__init__()

    def configure_arguments(self, env, parser):
        parser.add_argument('commandlet',
                            help    = 'Commandlet name',
                            metavar = '<command>')

        parser.add_argument('args',
                            help    = 'Commandlet arguments',
                            metavar = '<args>',
                            nargs    = argparse.REMAINDER)

        return True

    def is_available(self, env):
        return nimp.unreal.is_unreal4_available(env)

    def run(self, env):
        return nimp.unreal.commandlet(env, env.commandlet, *env.args)

