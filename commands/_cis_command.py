# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
from commands._command      import *
from utilities.perforce     import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisCommand(Command):
    abstract = 1 # Vieux hackos pour que l'introspection n'instancie pas cette
                 # classe, on pourrait checker que le module ne commence pas par _

    #-------------------------------------------------------------------------
    def __init__(self, name, description):
        Command.__init__(self, name, description)

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        parser.add_argument('p4_client',
                            metavar = '<CLIENT_NAME>',
                            type    = str)

        parser.add_argument('--hard-clean',
                            help    = 'Remove all unversionned files',
                            action  = "store_true",
                            default = False)

        return self.cis_configure_arguments(context, parser)

    #---------------------------------------------------------------------------
    def cis_configure_arguments(self, context, parser):
        return False

    #---------------------------------------------------------------------------
    def run(self, context):
        if not p4_create_config_file(FARM_P4_PORT, FARM_P4_USER, FARM_P4_PASSWORD, context.p4_client):
            return False

        if not p4_clean_workspace():
            return False

        result = self._cis_run(context)

        p4_clean_workspace()

        return result

    def _cis_run(self, context):
        return False
