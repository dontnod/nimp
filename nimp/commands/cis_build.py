# -*- coding: utf-8 -*-

from nimp.commands._cis_command import *
from nimp.utilities.ue3         import *
from nimp.utilities.ue4         import *
from nimp.utilities.deployment  import *
from nimp.utilities.file_mapper import *

#-------------------------------------------------------------------------------
class CisBuildCommand(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self,
                            'cis-build',
                            'Build UE3 or UE4 executable and publishes it to a shared directory')

    #---------------------------------------------------------------------------
    def cis_configure_arguments(self, env, parser):
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


        parser.add_argument('--publish-only',
                            help    = "Don't build game, publish binaries and symbols only.",
                            action  = "store_true",
                            default = False)

        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, env):
        env.generate_version_file = True

        if not env.publish_only:
            log_notification(log_prefix() + "Building game…")

            # Unreal Engine 4
            if hasattr(env, 'project_type') and env.project_type is 'UE4':
                if not ue4_build(env):
                    return False

            # Unreal Engine 3
            if hasattr(env, 'project_type') and env.project_type is 'UE3':
                if not ue3_build(env):
                    return False


        log_notification(log_prefix() + "Publishing Binaries…")
        files_to_publish = env.map_files().to(env.publish_binaries).load_set("binaries")
        if not all_map(robocopy, files_to_publish()):
            return False


        log_notification(log_prefix() + "Publishing symbols…")
        symbols_to_publish = env.map_files().load_set("symbols")
        if not upload_symbols(env, symbols_to_publish()):
            return False

        return True

