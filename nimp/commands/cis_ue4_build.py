# -*- coding: utf-8 -*-

from nimp.commands._cis_command import *
from nimp.utilities.ue4         import *
from nimp.utilities.deployment  import *
from nimp.utilities.file_mapper import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisUe4BuildCommand(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self,
                            'cis-ue4-build',
                            'Build UE4 executable and publishes it to a shared directory')

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

        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, env):
        log_notification(" ****** Building game...")
        env.generate_version_file = True

        with p4_transaction("Binaries checkout",
                            submit_on_success = False,
                            revert_unchanged = False,
                            add_not_versioned_files = False) as transaction:
            files_to_checkout = env.map_files()
            files_to_checkout.load_set("Binaries")
            if not all_map(checkout(transaction), files_to_checkout()):
                log_error("Error while checkouting binaries")
                return False

            if not ue4_build(env):
                return False

            log_notification(" ****** Publishing Binaries...")
            files_to_publish = env.map_files()
            files_to_publish.to(env.cis_binaries_directory).load_set("Binaries")
            if not all_map(robocopy, files_to_publish()):
                return False

            log_notification(" ****** Publishing symbols...")
            if env.is_microsoft_platform:
                if not upload_microsoft_symbols(env, ["Binaries/{0}".format(env.platform)]):
                    return False

        return True
