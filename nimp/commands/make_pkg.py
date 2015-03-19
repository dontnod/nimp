# -*- coding: utf-8 -*-

from nimp.commands._command     import *
from nimp.utilities.packaging   import *

#-------------------------------------------------------------------------------
class MakePkg(Command):

    def __init__(self):
        Command.__init__(self, 'make-pkg', 'Generate pkgs from loose files')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        parser.add_argument('source',
                    help    = 'Loose files directory',
                    metavar = '<DIR>')

        parser.add_argument('destination',
                    help    = 'Destination Directory',
                    metavar = '<DIR>')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'Platform to generate packages for',
                            metavar = '<platform>')

        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        return make_packages(context, context.source, context.destination)
