# -*- coding: utf-8 -*-

from nimp.commands._cis_command      import *
from nimp.utilities.ue3              import *
from nimp.utilities.ue3_deployment   import *

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
        if not ue3_build(context.solution,
                         context.platform,
                         context.configuration,
                         context.vs_version,
                         True):
            return False

        log_notification(" ****** Publishing Binaries...")
        copy = copy_files(context.to(context.cis_binaries_directory)
        ue3_publish_binaries(copy)
        if not copy.do():
            return False

        log_notification(" ****** Publishing symbols...")
        if context.platform.lower() in ["win64", "win32", "dingo", "xbox360"]:
            if not upload_microsoft_symbols(context, ["Binaries/{0}".format(context.platform)]):
                return False

        return True
