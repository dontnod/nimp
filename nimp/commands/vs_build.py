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
''' Build commands '''

import os

import nimp.command
import nimp.build
import nimp.environment

class VsBuild(nimp.command.Command):
    ''' Compiles a Visual Studio project '''
    def __init__(self):
        super(VsBuild, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'platform', 'configuration')
        return True

    def run(self, env):
        for file in os.listdir('.'):
            if os.path.splitext(file)[1] == '.sln' and os.path.isfile(file):
                platform, config = 'Any CPU', 'Release'
                if hasattr(env, 'platform') and env.platform is not None:
                    platform = env.platform
                if hasattr(env, 'configuration') and env.configuration is not None:
                    config = env.configuration

                sln = open(file).read()
                vsver = '11'
                if '# Visual Studio 2012' in sln:
                    vsver = '11'
                elif '# Visual Studio 2013' in sln:
                    vsver = '12'

                return nimp.build.vsbuild(file, platform, config, env.target, vsver, 'Build')

        return False

