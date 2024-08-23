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

'''Build commands'''

import logging
import os
import re

import nimp.build
import nimp.command
import nimp.environment
import nimp.unreal_engine.build


class Build(nimp.command.Command):
    '''Build a project'''

    def __init__(self):
        super(Build, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'platform', 'configuration', 'target', 'revision')

        parser.add_argument('--sln', help='Visual Studio solution to build)', metavar='<sln>')

        parser.add_argument(
            '--bootstrap', help='bootstrap or regenerate project files, if applicable', action='store_true'
        )

        parser.add_argument('--disable-unity', help='disable unity build', action='store_true')

        parser.add_argument(
            '--fastbuild', help='activate FASTBuild (implies --disable-unity for now)', action='store_true'
        )

        parser.add_argument(
            '--vs-version',
            help='version of Visual Studio to use, if applicable',
            default=(env.vs_version if hasattr(env, 'vs_version') else None),
        )

        parser.add_argument(
            '--enable-binaries-versioning',
            help='activate binaries versioning, useful for build systems',
            action='store_true',
        )

        parser.add_argument('--verbose', help='activate most verbose mode when available', action='store_true')

        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        # Special support for Unreal projects
        if env.is_unreal:
            env.ubt_version = False
            if Build._has_binaries_versioning(env):
                env.ubt_version = Build._compute_versioning_tag(env)

            # Use distcc and/or ccache if available
            nimp.build.install_distcc_and_ccache()
            return nimp.unreal_engine.build.build(env)

        nimp.environment.execute_hook('prebuild', env)

        sln = env.sln
        if sln is None:
            sln = Build._find_vs_solution()
            if sln is None:
                logging.error('Could not find a solution in current working directory. Use --sln to specify one')
                return False
        if not os.path.isfile(sln) or os.path.splitext(sln)[1] != '.sln':
            logging.error('sln filepath provided is invalid (sln: "%s")', sln)
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
            command = ['nuget.exe', 'update', '-self']
            if nimp.sys.process.call(command) != 0:
                logging.warning('NuGet could not update itself.')
            command = [
                'nuget.exe',
                'restore',
                sln,
                '-Recursive',
                '-Force',
                '-NonInteractive',
            ]
            if nimp.sys.process.call(command) != 0:
                logging.warning('NuGet could not restore packages.')

        if hasattr(env, 'vs_version') and env.vs_version:
            vs_version = env.vs_version
        else:
            contents = open(sln).read()
            vs_version = '14'
            if 'MinimumVisualStudioVersion = 15' in contents:
                vs_version = '15'

        if not nimp.build.vsbuild(sln, platform, config, project=env.target, vs_version=vs_version, target='Build'):
            return False

        nimp.environment.execute_hook('postbuild', env)

        return True

    @staticmethod
    def _has_binaries_versioning(env):
        has_binaries_versioning = hasattr(env, 'enable_binaries_versioning') and env.enable_binaries_versioning
        has_revision = hasattr(env, 'revision') and env.revision is not None
        if has_binaries_versioning:
            assert has_revision, "A revision is needed for binaries versioning"
        return has_binaries_versioning and has_revision

    @staticmethod
    def _compute_versioning_tag(env):
        branch = ""
        if hasattr(env, 'branch') and env.branch is not None:
            branch = f'{env.branch}-'
        revision = env.revision
        if nimp.utils.git.is_full_sha1(revision):
            revision = env.revision[:8]

        return f'{branch}{revision}'

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
        with open(sln, 'r') as fp:
            for line in fp.readlines():
                if 'GlobalSection(SolutionConfigurationPlatforms)' in line:
                    good_section = True
                elif 'EndGlobalSection' in line:
                    good_section = False
                elif good_section:
                    m = entry.match(line.strip())
                    if m:
                        configs.add(m.groups(0)[0])
                        platforms.add(m.groups(0)[1])
            return configs, platforms
