# -*- coding: utf-8 -*-

import os

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *
from nimp.utilities.build import *

#-------------------------------------------------------------------------------
class BuildCommand(Command):

    def __init__(self):
        Command.__init__(self, 'build', 'Build UE3 or UE4 executable')

    #---------------------------------------------------------------------------
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

    #---------------------------------------------------------------------------
    def run(self, env):

        # Use distcc and/or ccache if available
        install_distcc_and_ccache()

        # Unreal Engine 4
        if env.is_ue4:
            return ue4_build(env)

        # Unreal Engine 3
        if env.is_ue3:
            return ue3_build(env)

        # Visual Studio maybe?
        for f in os.listdir('.'):
            if os.path.splitext(f)[1] == '.sln' and os.path.isfile(f):
                sln = open(f).read()
                vsver = '11'
                if '# Visual Studio 2012' in sln:
                    vsver = '11'
                elif '# Visual Studio 2013' in sln:
                    vsver = '12'
                return vsbuild(f, 'Any CPU', 'Release', env.target, vsver, 'Build')

        # Error!
        log_error("Invalid project type {0}" % (env.project_type))
        return False

