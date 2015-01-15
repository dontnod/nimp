# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
from commands.cis_command       import *
from utilities.ue3              import *
from utilities.ue3_deployment   import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisUe3BuildCommand(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-ue3-build', 'Build UE3 executable and publishes it to a shared directory')

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
                            '--configuration',
                            help    = 'configuration to build',
                            metavar = '<configuration>')

        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, context):
        settings  = context.settings
        arguments = context.arguments

        if not ue3_build(settings.solution_file, arguments.platform, arguments.configuration, settings.vs_version, True):
            return False

        if not ue3_publish_binaries(settings.cis_binaries_directory,
                                    settings.project_name,
                                    settings.game,
                                    arguments.revision,
                                    get_deployment_platform(arguments.platform),
                                    arguments.configuration):
            return False

        return True