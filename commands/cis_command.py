# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
from commands.command       import *
from utilities.perforce     import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisCommand(Command):
    abstract = 1
    #-------------------------------------------------------------------------
    def __init__(self, name, description):
        Command.__init__(self, name, description)

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('p4_client',
                            metavar = '<CLIENT_NAME>',
                            type    = str)

        parser.add_argument('--hard-clean',
                            help    = 'Remove all unversionned files',
                            action  = "store_true",
                            default = False)

        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        arguments = context.arguments

        if not p4_create_config_file(FARM_P4_PORT, FARM_P4_USER, FARM_P4_PASSWORD, arguments.p4_client):
            return False

        if not p4_clean_workspace():
            return False

        result = self._cis_run(context)

        p4_clean_workspace()

        return result

    def _cis_run(self, context):
        return False
