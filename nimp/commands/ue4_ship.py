# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue4 import *

#-------------------------------------------------------------------------------
class Ue3ShipCommand(Command):
    def __init__(self):
        Command.__init__(self, 'ue4-ship', 'Generate shippable loose files in target directory')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('destination',
                            help    = 'Destination Directory',
                            metavar = '<DIR>')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to publish',
                            metavar = '<platform>')

        parser.add_argument('--dlc',
                            help    = 'Dlc to ship',
                            metavar = '<dlc>',
                            default = None)

        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        return ue4_ship(env, env.destination)
