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

import nimp.command
import nimp.build
import nimp.environment
import nimp.unreal

class Build(nimp.command.Command):
    ''' Builds a project binaries '''
    def __init__(self):
        super(Build, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'platform', 'configuration', 'target')

        parser.add_argument('--bootstrap',
                            help = 'bootstrap or regenerate project files, if applicable',
                            action = "store_true",
                            default = False)

        parser.add_argument('--disable-unity',
                            help = 'disable unity build',
                            action = "store_true",
                            default = False)

        parser.add_argument('--fastbuild',
                            help = 'activate FASTBuild (implies --disable-unity for now)',
                            action = 'store_true',
                            default = False)

        return True

    def is_available(self, env):
        return nimp.unreal.is_unreal4_available(env)

    def run(self, env):
        # Use distcc and/or ccache if available
        nimp.build.install_distcc_and_ccache()

        return nimp.unreal.build(env)
