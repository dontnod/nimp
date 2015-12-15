# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.build import *

#-------------------------------------------------------------------------------
class VsBuildCommand(Command):

    def __init__(self):
        Command.__init__(self, 'vs-build', 'Builds a Visual Studio project')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('solution',
                            help    = 'Solution file',
                            metavar = '<FILE>')

        parser.add_argument('project',
                            help    = 'Project',
                            metavar = '<FILE>',
                            default = 'None')

        parser.add_argument('--target',
                            help    = 'Target',
                            metavar = '<TARGET>',
                            default = 'Build')

        parser.add_argument('-c',
                            '--vs-configuration',
                            help    = 'configuration to build',
                            metavar = '<vs-configuration>',
                            default = 'release')

        parser.add_argument('-p',
                            '--vs-platform',
                            help    = 'platform to build',
                            metavar = '<vs-platform>',
                            default = 'Win64')

        parser.add_argument('--vs-version',
                            help    = 'VS version to use',
                            metavar = '<VERSION>',
                            default = '12')
        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        return vsbuild(env.format(env.solution), env.vs_platform, env.vs_configuration, env.project, env.vs_version, env.target)
