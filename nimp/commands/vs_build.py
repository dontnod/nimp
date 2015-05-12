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
                            '--configuration',
                            help    = 'configuration to build',
                            metavar = '<configuration>',
                            default = 'release')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platform to build',
                            metavar = '<platform>',
                            default = 'Win64')

        parser.add_argument('--vs-version',
                            help    = 'VS version to use',
                            metavar = '<VERSION>',
                            default = '12')
        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        return vsbuild(env.build['solution'], env.platform, env.configuration, env.project['name'], env.build['vs_version'], env.target)
