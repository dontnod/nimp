# -*- coding: utf-8 -*-

from commands._cis_command      import *
from utilities.ue3              import *
from utilities.ue3_deployment   import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisUe3CookCommand(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-ue3-cook', 'Cooks game and publishes result.')

    #---------------------------------------------------------------------------
    def cis_configure_arguments(self, context, parser):
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
        if dlc is not None:
            if not self._deploy_game_cook(context):
                return False

        copy = CopyTransaction(context)
        copy.add(context.cis_version_directory)
        if not copy.do():
            return False

        map = context.cook_maps[(context.dlc or 'default').lower()]

        if not context.call(ue3_cook, map = map):
            return False

        cook_destination = context.cis_cook_directory if dlc is None else context.cis_dlc_cook_directory

        if not publish(context, ue3_publish_cook, cook_destination):
            return False

        return True

    def _deploy_game_cook(self, context):
        freezed_cook_directory = context.format(context.freezed_cook_directory)
        dlc                    = context.dlc

        if os.path.exists(freezed_cook_directory):
            game_cook_directory = freezed_cook_directory
        else:
            cook_revision = context.call(get_latest_available_revision,
                                         context.cis_cook_directory,
                                         platforms       = ['Win64'],
                                         start_revision  =  arguments.revision)

            if cook_revision is None:
                log_error("Unable to find Episode 01 cook for revision {0}. Please build it.", context.revision)
                return False

            log_notification("Using game cook from revision {0}", revision)
            game_cook_directory = context.cis_cook_directory

        if not deploy(context, game_cook_directory):
            log_error("Unable to deploy game cook")
            return False

