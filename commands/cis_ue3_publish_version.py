# -*- coding: utf-8 -*-

from commands._cis_command      import *
from utilities.ue3              import *
from utilities.ue3_deployment   import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisUe3PublishVersion(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-ue3-publish-version', 'Gets built binaries and publishes an internal version.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        CisCommand.configure_arguments(self, context, parser)
        parser.add_argument('-r',
                            '--revision',
                            help    = 'Current revision',
                            metavar = '<revision>')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to build',
                            metavar = '<platform>')

        parser.add_argument('-c',
                            '--configurations',
                            help    = 'Configurations to deploy',
                            metavar = '<platform>',
                            nargs = '+')
        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, context):
        for configuration in context.configurations:
            if not deploy(context, context.cis_binaries_directory, configuration = configuration):
                log_error("Unable to compiled binaries for revision {0} and platform {1}, can't publish version.", context.revision, context.platform)
                return False

        if context.platform.lower() == 'win64':
            if not ue3_build_script(context.game):
                log_error("Error while building script")
                return False

        if not publish(context, ue3_publish_version, context.cis_version_directory):
            return False

        return True
