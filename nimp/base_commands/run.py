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

''' Command to run executables or special commands '''

import argparse
import logging

import nimp.command
import nimp.unreal
import nimp.sys.process

class Run(nimp.command.Command):
    ''' Run executables, hooks, and commandlets '''
    def configure_arguments(self, env, parser):
        parser.add_argument('parameters',
                            help='command to run',
                            metavar='<command> [<argument>...]',
                            nargs=argparse.REMAINDER)
        parser.add_argument('--hook',
                            help='run as hook (prerun, postbuild, etc.)',
                            metavar='hook')
        parser.add_argument('--commandlet',
                            help='run as Unreal Engine commandlet (resavepackages, deriveddatacache, etc.)',
                            action='store_true')
        return True


    def is_available(self, env):
        return True, ''


    def run(self, env):

        # Hook mode
        if hasattr(env, 'hook') and env.hook:
            if len(env.parameters) != 0:
                logging.error('Too many arguments')
                return False
            return nimp.environment.execute_hook(env.hook, env)

        # Commandlet mode
        if hasattr(env, 'commandlet') and env.commandlet:
            if not nimp.unreal.is_unreal4_available(env):
                logging.error('Not an Unreal Engine project')
                return False
            return nimp.unreal.commandlet(env, env.parameters[0], env.parameters[1:])

        # Standard executable mode
        cmdline = []
        for arg in env.parameters:
            cmdline.append(env.format(arg))

        nimp.environment.execute_hook('prerun', env)
        ret = nimp.sys.process.call(cmdline)
        nimp.environment.execute_hook('postrun', env)

        return ret == 0
