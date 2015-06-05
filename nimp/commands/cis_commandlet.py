# -*- coding: utf-8 -*-

from nimp.commands._cis_command import *
from nimp.utilities.ue4         import *
from nimp.utilities.deployment  import *
from nimp.utilities.packaging   import *

#-------------------------------------------------------------------------------
class CisCommandlet(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-commandlet', 'Executes an unreal commandlet.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        CisCommand.configure_arguments(self, env, parser)

        parser.add_argument('commandlet',
                            help    = 'Commandlet name',
                            metavar = '<COMMAND>')

        parser.add_argument('args',
                            help    = 'Commandlet arguments',
                            metavar = '<ARGS>',
                            nargs   = '*')

        parser.add_argument('-r',
                            '--revision',
                            help    = 'Current revision',
                            metavar = '<revision>',
                            default = None)

        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, env):
        with deploy_latest_revision(env, env.publish_version, env.revision, ['Win64']):
            return ue4_commandlet(env, env.commandlet, *env.args)