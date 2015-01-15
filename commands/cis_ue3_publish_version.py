# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
from commands.cis_command       import *
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

        project  = settings.project_name
        game     = settings.game
        revision = arguments.revision
        platform = get_deployment_platform(arguments.platform)

        for configuration in arguments.configurations:
            if not deploy(settings.cis_binaries_directory,
                          project          = project,
                          game             = game,
                          revision         = revision,
                          platform         = platform,
                          configuration    = configuration):
                log_error("Unable to compiled binaries for revision {0} and platform {1}, can't publish version.", revision)
                return False

        if platform.lower() == 'win64':
            if not ue3_build_script(context):
                log_error("Error while building script")
                return False

        if not ue3_publish_version(settings.cis_version_directory, project, game, revision, platform):
            return False

        return True