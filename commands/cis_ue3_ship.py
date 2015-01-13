# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
from commands.cis_command   import *
from utilities.ue3           import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisUe3Ship(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-ue3-ship', 'Cooks and publish a final version.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        CisCommand.configure_arguments(self, context, parser)
        settings = context.settings

        parser.add_argument('-r',
                            '--revision',
                            help    = 'Current revision',
                            metavar = '<revision>',
                            default = None)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to publish',
                            metavar = '<platform>')

        parser.add_argument('-c',
                            '--configuration',
                            help    = 'Configurations to publish',
                            metavar = '<platform>',
                            choices = ['test', 'final'])
        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, context):
        settings  = context.settings
        arguments = context.arguments

        if not _deploy_revision(context):
            return False

        return True

#-------------------------------------------------------------------------------
def _deploy_revision(context):
    settings  = context.settings
    arguments = context.arguments
    revision  = arguments.revision or get_latest_available_revision(settings.cis_version_directory,
                                                                    platforms = ['Win64', arguments.platform],
                                                                    project   = settings.project_name,
                                                                    game      = settings.game)

    if not ue3_deploy_version(settings.cis_version_directory,
                              project   = settings.project_name,
                              game      = settings.game,
                              revision  = revision,
                              platform  = 'Win64'):
        return False

    if not ue3_deploy_version(settings.cis_version_directory,
                              project   = settings.project_name,
                              game      = settings.game,
                              revision  = revision,
                              platform  = arguments.platform):
        return False
