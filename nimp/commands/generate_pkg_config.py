# -*- coding: utf-8 -*-

from nimp.commands._command     import *
from nimp.utilities.packaging   import *

#-------------------------------------------------------------------------------
class GeneratePkgConfig(Command):

    def __init__(self):
        Command.__init__(self, 'generate-pkg-config', 'Generate pkgs files')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        parser.add_argument('loose_files_directory',
                    help    = 'Loose files directory',
                    metavar = '<DIR>')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'Platform to generate packages for',
                            metavar = '<platform>')

        parser.add_argument('--dlc',
                            help    = 'Dlc to cook',
                            metavar = '<dlc>',
                            default = None)
        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        return generate_pkg_config(context)
