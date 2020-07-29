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

''' Build commands '''

import logging
import os
import re

import nimp.build
import nimp.command
import nimp.environment
import nimp.ue4.build

class Build(nimp.command.Command):
    ''' Builds a project binaries '''
    def __init__(self):
        super(Build, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser,
                                          'platform',
                                          'configuration',
                                          'target',
                                          'revision')

        parser.add_argument('--bootstrap',
                            help='bootstrap or regenerate project files, if applicable',
                            action='store_true')

        parser.add_argument('--disable-unity',
                            help='disable unity build',
                            action='store_true')

        parser.add_argument('--fastbuild',
                            help='activate FASTBuild (implies --disable-unity for now)',
                            action='store_true')

        parser.add_argument('--vs-version',
                            help='version of Visual Studio to use, if applicable',
                            default=(env.vs_version if hasattr(env, 'vs_version') else None))

        return True

    def is_available(self, env):
        available = env.is_ue4 or Build._find_vs_solution() is not None
        return (available, ('Nothing found to build. Check that you are either'
                            ' in an Unreal Engine project directory, or that'
                            ' there is a .sln file in current directory'))

    def run(self, env):

        # Special support for UE4 projects
        if env.is_ue4:
            # Use distcc and/or ccache if available
            nimp.build.install_distcc_and_ccache()
            return nimp.ue4.build.build(env)

        nimp.environment.execute_hook('prebuild', env)

        sln = Build._find_vs_solution()
        if sln is None:
            return False

        # Try to use the best default config/platform combination
        configs, platforms = Build._find_configs_platforms(sln)

        platform = next((p for p in ['x64', 'Win64', 'Any CPU', 'Win32'] if p in platforms), 'Any CPU')
        config = next((c for c in ['Release', 'Debug'] if c in configs), 'Release')

        if hasattr(env, 'platform') and env.platform is not None:
            platform = env.platform
        if hasattr(env, 'configuration') and env.configuration is not None:
            config = env.configuration

        if hasattr(env, 'bootstrap') and env.bootstrap:
            command = [ 'nuget.exe', 'update', '-self' ]
            if nimp.sys.process.call(command) != 0:
                logging.warning('NuGet could not update itself.')
            command = [ 'nuget.exe', 'restore', sln ]
            if nimp.sys.process.call(command) != 0:
                logging.warning('NuGet could not restore packages.')

        if hasattr(env, 'vs_version') and env.vs_version:
            vs_version = env.vs_version
        else:
            contents = open(sln).read()
            vs_version = '14'
            if 'MinimumVisualStudioVersion = 15' in contents:
                vs_version = '15'

        if not nimp.build.vsbuild(sln, platform, config,
                                  project=env.target,
                                  vs_version=vs_version,
                                  target='Build'):
            return False

        nimp.environment.execute_hook('postbuild', env)

        return True

    @staticmethod
    def _find_vs_solution():
        for it in os.listdir('.'):
            if os.path.splitext(it)[1] == '.sln' and os.path.isfile(it):
                return it
        return None

    @staticmethod
    def _find_configs_platforms(sln):
        configs, platforms = set(), set()
        entry = re.compile('\s*([^|]*)\|([^=]*) = ([^|]*)\|([^|]*)')

        good_section = False
        for l in open(sln, 'r').readlines():
            if 'GlobalSection(SolutionConfigurationPlatforms)' in l:
                good_section = True
            elif 'EndGlobalSection' in l:
                good_section = False
            elif good_section:
                m = entry.match(l.strip())
                if m:
                    configs.add(m.groups(0)[0])
                    platforms.add(m.groups(0)[1])
        return configs, platforms
