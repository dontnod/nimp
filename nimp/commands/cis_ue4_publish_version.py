# -*- coding: utf-8 -*-

import shutil

from nimp.commands._cis_command import *
from nimp.utilities.ue4         import *
from nimp.utilities.file_mapper import *
from nimp.utilities.deployment  import *

#-------------------------------------------------------------------------------
class CisUe4PublishVersion(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-ue4-publish-version', 'Gets built binaries and publishes an internal version.')

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
            for configuration in env.configurations:
                files_to_deploy.override(configuration = configuration).src(env.cis_binaries_directory).glob("**")

            log_notification("[nimp] Deploying binaries…")
            if not all_map(checkout_and_copy(trans), files_to_deploy()):
                return False

            if not env.keep_temp_binaries:
                for configuration in env.configurations:
                    try:
                        shutil.rmtree(env.format(env.cis_binaries_directory, configuration = configuration))
                    except Exception as ex:
                        log_error("[nimp] Error while cleaning binaries : {0}", ex)

            files_to_publish = env.map_files().to(env.cis_version_directory)
            log_notification("[nimp] Publishing version {0}…", configuration)
            files_to_publish.load_set("Version")
            if not all_map(robocopy, files_to_publish()):
                return False

        return True
