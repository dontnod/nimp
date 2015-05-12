# -*- coding: utf-8 -*-

import shutil

from nimp.commands._cis_command import *
from nimp.utilities.ue3         import *
from nimp.utilities.file_mapper import *
from nimp.utilities.deployment  import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisUe3PublishVersion(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-ue3-publish-version', 'Gets built binaries and publishes an internal version.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        CisCommand.configure_arguments(self, env, parser)
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

        parser.add_argument('--keep-temp-binaries',
                            help    = 'Don\'t delete temporary binaries directory',
                            action  = "store_true",
                            default = False)
        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, env):
        with p4_transaction("Binaries Checkout",
                            submit_on_success = False,
                            revert_unchanged = False,
                            add_not_versioned_files = False) as trans:
            files_to_deploy = env.map_files()
            for configuration in env.build['configurations']:
                files_to_deploy.override(configuration = configuration).src(env.publish['binaries']).glob("**")

            log_notification("[nimp] Deploying binaries…")
            if not all_map(checkout_and_copy(trans), files_to_deploy()):
                return False

            if not env.keep_temp_binaries:
                for configuration in env.build['configurations']:
                    try:
                        shutil.rmtree(env.format(env.publish['binaries'], configuration = configuration))
                    except Exception as ex:
                        log_error("[nimp] Error while cleaning binaries : {0}", ex)

            if env.is_win64:
                log_notification("[nimp] Building script…")
                if not ue3_build_script(env.project['game_name']):
                    log_error("[nimp] Error while building script")
                    return False

            files_to_publish = env.map_files().to(env.publish['version'])
            log_notification("[nimp] Publishing version {0}…", configuration)
            files_to_publish.load_set("Version")
            if not all_map(robocopy, files_to_publish()):
                return False

        return True
