# -*- coding: utf-8 -*-

from nimp.commands._cis_command      import *
from nimp.utilities.ue3              import *
from nimp.utilities.ue3_deployment   import *

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
        copy = CopyTransaction(context, ".", checkout = True)
        for configuration in context.configurations:
            copier.override(configuration = configuration).add(context.cis_binaries_directory)

        if not copy.do():
            return False

        if context.platform.lower() == 'win64':
            if not ue3_build_script(context.game):
                log_error("Error while building script")
                return False

        copy = CopyTransaction(context, context.cis_version_directory, platform = get_binaries_platform(context.platform))
        ue3_publish_version(copy)
        if not copy.do():
            return False

        return True
