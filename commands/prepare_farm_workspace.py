# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import shutil

from commands.command       import *
from commands.vsbuild       import *

from config.system          import *

from utilities.files        import *
from utilities.hashing      import *
from utilities.paths        import *
from utilities.perforce     import *
from utilities.processes    import *

# TODO : Remove all non-versionned files from the repository
# TODO : Add Clean Wwise cache

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class PrepareFarmWorskpaceCommand(Command):

    def __init__(self):
        Command.__init__(self, 'prepare-farm-workspace', 'Prepares a farm workspace.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('p4_client',
                            metavar = '<CLIENT_NAME>',
                            type    = str)

        parser.add_argument('--revert-only',
                            help    = 'Don\'t clean unversionned files, only revert pending changelists',
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




