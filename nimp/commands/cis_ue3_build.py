# -*- coding: utf-8 -*-

from nimp.commands._cis_command     import *
from nimp.utilities.ue3             import *
from nimp.utilities.deployment      import *
from nimp.utilities.file_mapper     import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisUe3BuildCommand(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self,
                            'cis-ue3-build',
                            'Build UE3 executable and publishes it to a shared directory')

    #---------------------------------------------------------------------------
    def cis_configure_arguments(self, context, parser):
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
    def _cis_run(self, context):
        log_notification(" ****** Building game...")
        context.generate_version_file = True

        with p4_transaction("Binaries checkout",
                            submit_on_success = False,
                            revert_unchanged = False,
                            add_not_versioned_files = False) as transaction:
            files_to_checkout = context.map_files()
            files_to_checkout.load_set("Binaries")
            if not all_map(checkout(transaction), files_to_checkout()):
                return False

            if not ue3_build(context):
                return False

            log_notification(" ****** Publishing Binaries...")
            files_to_publish = context.map_files()
            files_to_publish.to(context.cis_binaries_directory).load_set("Binaries")
            if not all_map(robocopy, files_to_publish()):
                return False

            log_notification(" ****** Publishing symbols...")
            if context.is_microsoft_platform:
                if not upload_microsoft_symbols(context, ["Binaries/{0}".format(context.platform)]):
                    return False

        return True
