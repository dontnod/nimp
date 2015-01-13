# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
from commands.cis_command   import *
from utilities.ue3           import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisUe3BuildCommand(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-ue3-publish-version', 'Gets built binaries and publishes an internal version.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        CisCommand.configure_arguments(self, context, parser)
        settings = context.settings

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
        settings  = context.settings
        arguments = context.arguments

        for configuration in arguments.configurations:
            if not ue3_deploy_and_clean_binaries(settings.cis_binaries_directory,
                                                 settings.project_name,
                                                 settings.game,
                                                 arguments.revision,
                                                 arguments.platform,
                                                 configuration):
                return False

        if not ue3_publish_version(settings.cis_version_directory,
                                   settings.project_name,
                                   settings.game,
                                   arguments.revision,
                                   arguments.platform):
            return False

        return True