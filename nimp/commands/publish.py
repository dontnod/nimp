# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *
from nimp.utilities.deployment import *
from nimp.utilities.file_mapper import *

#-------------------------------------------------------------------------------
class PublishCommand(Command):
    def __init__(self):
        Command.__init__(self,
                         'publish',
                         'Publish binaries or symbols')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('-r',
                            '--revision',
                            help = 'Current revision',
                            metavar = '<revision>')

        parser.add_argument('-p',
                            '--platform',
                            help = 'platforms to build',
                            metavar = '<platform>')

        parser.add_argument('-c',
                            '--configuration',
                            help = 'configuration to build',
                            metavar = '<configuration>')

        parser.add_argument('-m',
                            '--mode',
                            help = 'operating mode (binaries, symbols)',
                            metavar = '<mode>')

        return True

    #---------------------------------------------------------------------------
    def run(self, env):

        if not hasattr(env, 'mode') or env.mode == 'binaries':

            log_notification(log_prefix() + "Publishing Binaries…")

            files_to_publish = env.map_files().to(env.publish_binaries).load_set("binaries")
            if not all_map(robocopy, files_to_publish()):
                return False

        elif env.mode == 'symbols':

            log_notification(log_prefix() + "Publishing symbols…")

            symbols_to_publish = env.map_files().load_set("symbols")
            if not upload_symbols(env, symbols_to_publish()):
                return False

        return True

