# -*- coding: utf-8 -*-

from nimp.commands._cis_command      import *
from nimp.utilities.ue4              import *
from nimp.utilities.deployment       import *
from nimp.utilities.packaging        import *

#-------------------------------------------------------------------------------
class CisUe4Ship(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-ue4-ship', 'Cooks and publish a final version.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        CisCommand.configure_arguments(self, env, parser)

        parser.add_argument('-r',
                            '--revision',
                            help    = 'Current revision',
                            metavar = '<revision>',
                            default = None)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to publish',
                            metavar = '<platform>')

        parser.add_argument('--dlc',
                            help    = 'Dlc to cook',
                            metavar = '<dlc>',
                            default = None)
        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, env):
        return ue4_ship(env, env.destination)
