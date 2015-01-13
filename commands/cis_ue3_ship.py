# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
from commands.cis_command       import *
from utilities.ue3              import *
from utilities.ue3_deployment   import *

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

        parser.add_argument('--dlc',
                            help    = 'Dlc to cook',
                            metavar = '<platform>',
                            default = None)
        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, context):
        settings  = context.settings
        arguments = context.arguments

        project         = settings.project_name
        game            = settings.game
        languages       = settings.languages
        dlc             = arguments.dlc
        map             = settings.cook_maps[dlc or 'default']
        platform        = arguments.platform
        configuration   = arguments.configuration
        cook_directory  = settings.cis_cook_directory
        revision        = arguments.revision

        if not _deploy_revisions(context):
            return False

        if dlc is not None:
            if not deploy(settings.freezed_cook_directory,
                          project           = project,
                          game              = game,
                          platform          = platform,
                          configuration     = configuration,
                          revision          = revision):

                if not deploy(cook_directory,
                              project           = project,
                              game              = game,
                              platform          = platform,
                              configuration     = configuration,
                              revision          = revision):
                    return False

        if not ue3_cook(game, map, languages, dlc, platform, configuration):
            return False

        if dlc is None:
            if not ue3_publish_cook(cook_directory, project, game, platform, configuration, revision):
                return False

        return True

#-------------------------------------------------------------------------------
def _deploy_revisions(context):
    settings  = context.settings
    arguments = context.arguments
    revision  = arguments.revision or get_latest_available_revision(settings.cis_version_directory,
                                                                    platforms = ['Win64', arguments.platform],
                                                                    project   = settings.project_name,
                                                                    game      = settings.game)
    if not deploy(settings.cis_version_directory,
                  project  = settings.project_name,
                  game     = settings.game,
                  revision = revision,
                  platform = 'Win64'):
        return False

    if arguments.platform.lower() != 'win64':
        if not deploy(settings.cis_version_directory,
                      project  = settings.project_name,
                      game     = settings.game,
                      revision = revision,
                      platform = platform):
            return False

    return True