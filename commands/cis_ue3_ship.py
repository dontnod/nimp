# -*- coding: utf-8 -*-

from commands._cis_command      import *
from utilities.ue3              import *
from utilities.deployment       import *
from utilities.ue3_deployment   import *

#-------------------------------------------------------------------------------
class CisUe3Ship(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-ue3-ship', 'Cooks and publish a final version.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        CisCommand.configure_arguments(self, context, parser)

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
    def _cis_run(self, context):
        if not deploy_latest_revision(context, context.cis_version_directory, context.revision, ['Win64']):
            log_error("Unable to deploy Win64 binaries, aborting")
            return False

        if context.platform.lower() != "Win64":
            if not deploy_latest_revision(context, context.cis_version_directory, context.revision, [context.platform]):
                log_error("Unable to deploy {0} binaries, aborting", context.platform)
                return False

        if not ue3_ship(context):
            return False

        return True
