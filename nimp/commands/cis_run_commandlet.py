# -*- coding: utf-8 -*-

from nimp.commands._cis_command import *
from nimp.utilities.ue4         import *
from nimp.utilities.deployment  import *
from nimp.utilities.file_mapper import *

#-------------------------------------------------------------------------------
class CisCommandletCommand(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self,
                            'cis-commandlet',
                            'Runs a commandlet')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        CisCommand.configure_arguments(self, env, parser)

        parser.add_argument('commandlet',
                            help    = 'Commandlet name',
                            metavar = '<COMMANDLET>')

        parser.add_argument('-r',
                            '--revision',
                            help    = 'Current revision',
                            metavar = '<revision>',
                            default = None)

        parser.add_argument('--args',
                            help    = 'Arguments to give to the commandlet.',
                            nargs=2,
                            action='append',
                            default = [])

        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, env):
        with deploy_latest_revision(env, env.publish_version, env.revision, ['Win64']):
            return ue4_commandlet(env)
