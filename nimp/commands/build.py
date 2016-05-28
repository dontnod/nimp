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

import logging
import os

import nimp.commands.command
import nimp.utilities.build
import nimp.utilities.environment
import nimp.utilities.ue3
import nimp.utilities.ue4

class Build(nimp.commands.command.Command):
    ''' Compile an ue3 or ue4 projects '''
    def __init__(self):
        super(Build, self).__init__()

    def configure_arguments(self, env, parser):
        parser.add_argument('-c', '--configuration',
                            help = 'configuration to build',
                            metavar = '<configuration>')

        parser.add_argument('-p', '--platform',
                            help = 'platform to build',
                            metavar = '<platform>')

        parser.add_argument('-t', '--target',
                            help = 'target to build (game, editor, tools)',
                            metavar = '<target>')

        parser.add_argument('--bootstrap',
                            help = 'bootstrap or regenerate project files, if applicable',
                            action = "store_true",
                            default = False)

        parser.add_argument('--generate-version-file',
                            help = 'generate a C++ file with build information',
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

    def sanitize(self, env):
        nimp.utilities.environment.sanitize_platform(env)
        nimp.utilities.build.sanitize_config(env)
        nimp.utilities.ue3.sanitize(env)
        nimp.utilities.ue4.sanitize(env)
        if not hasattr(env, 'target') or env.target is None:
            if env.is_ue4:
                if env.platform in ['win64', 'mac', 'linux']:
                    env.target = 'editor'
                else:
                    env.target = 'game'
            elif env.is_ue3:
                if env.platform == 'win64':
                    env.target = 'editor'
                else:
                    env.target = 'game'

    def run(self, env):

        # Use distcc and/or ccache if available
        nimp.utilities.build.install_distcc_and_ccache()

        # Unreal Engine 4
        if env.is_ue4:
            return nimp.utilities.ue4.ue4_build(env)

        # Unreal Engine 3
        if env.is_ue3:
            return nimp.utilities.ue3.ue3_build(env)

        # Visual Studio maybe?
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

                return nimp.utilities.build.vsbuild(file, platform, config, env.target, vsver, 'Build')

        # Error! <- Are you f****g kidding me ?!!11
        logging.error("Invalid project type %s", env.project_type)
        return False

