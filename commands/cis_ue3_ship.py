# -*- coding: utf-8 -*-

from commands._cis_command      import *
from utilities.ue3              import *
from utilities.deployment       import *
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
                            metavar = '<dlc>',
                            default = None)
        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, context):
        if context.dlc is None:
            context.dlc = context.project

        #if not deploy_latest_revision(context, context.cis_version_directory, context.revision, ['Win64']):
        #    log_error("Unable to deploy Win64 binaries, aborting")
        #    return False

        master_directory = context.format(context.cis_master_directory)

        if os.path.exists(master_directory):
            if context.dlc == context.project:
                return _ship_game_patch(context)
            else:
                _ship_dlc_path(context)
        else:
            if context.dlc == context.project:
                _ship_game_gold(context)
            else:
                _ship_dlc_gold(context)
        # Checker s'il existe un dossier build/shipped/PLATFORM_Episode
        # Si oui, on crée un patch:
        #   S'il s'agit d'un DLC :
        #       On copie le cook du master E1 en local
        #   On copie le cook en local
        #   On lance un cook incrémental
        #   On met de cote les fichiers a garder
        #   On delete et recopie le cook d'origine
        #   On copie les fichiers a garder
        # Sinon, on crée un DLC
        #   S'il s'agit d'un DLC
        #       On Copie le cook du master E1 en local
        # On appelle CookerSync
        settings  = context.settings
        arguments = context.arguments

        return True

def _ship_game_patch(context):
    #if not deploy(context, context.cis_master_directory):
    #    return False

    patch_config_file = context.format(context.patch_config_path)

    if not context.load_config_file(patch_config_file):
        log_error("Unable to load path config file at {0}", patch_config_file)
        return False

    map = context.cook_maps[context.dlc]

    if not ue3_cook(context.game,
                    map,
                    context.languages,
                    None,
                    context.platform,
                    context.configuration,
                    incremental = True):
        return False

    cook_directory  = ".\ExampleGame\Cooked%sFinal" % get_cook_platform_name(context.platform)
    patched_files   = context.patched_files(context, cook_directory)

    log_notification("Redeploying master cook ignoring patched files")
    if not deploy(context, context.cis_master_directory, ignore_files = patched_files):
        return False

    if not publish(context, ue3_publish_patch, context.cis_ship_patch_directory):
        return False

    return True
