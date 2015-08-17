# -*- coding: utf-8 -*-

from nimp.commands._cis_command import *
from nimp.utilities.ue3         import *
from nimp.utilities.ue4         import *
from nimp.utilities.deployment  import *
from nimp.utilities.packaging   import *
from nimp.utilities.file_mapper import *

#-------------------------------------------------------------------------------
class Commandlet(Command):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'commandlet', 'Executes an Unreal commandlet.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('commandlet',
                            help    = 'Commandlet name',
                            metavar = '<COMMAND>')

        parser.add_argument('args',
                            help    = 'Commandlet arguments',
                            metavar = '<ARGS>',
                            nargs    = argparse.REMAINDER)

        parser.add_argument('-r',
                            '--revision',
                            help    = 'Current revision',
                            metavar = '<revision>',
                            default = None)

        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        # Unreal Engine 4
        if env.is_ue4:
            return ue4_commandlet(env, env.commandlet, *env.args)

        # Unreal Engine 3
        if env.is_ue3:
            return ue3_commandlet(env.game, env.commandlet, list(env.args))

