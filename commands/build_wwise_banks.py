# -*- coding: utf-8 -*-

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

#-------------------------------------------------------------------------------
class BuildWwiseBanksCommand(Command):
    #---------------------------------------------------------------------------
    def __init__(self):
        Command.__init__(self, 'build-wwise-banks', 'Builds Wwise Banks')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('platform',
                            help    = 'Platform to build',
                            metavar = '<PLATFORM>')

        parser.add_argument('--checkin',
                            help    = 'Automatically checkin result',
                            action  = "store_true",
                            default = False)
        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        settings = context.settings
        arguments = context.arguments

        platform_dir     = arguments.platform if arguments.platform.lower() != "xbox360" else "X360"
        wwise_banks_path = os.path.join(settings.wwise_banks_path, platform_dir)
        cl_name          = "[CIS] Updated {0} Wwise Banks".format(arguments.platform)
        workspace        = p4_get_first_workspace_containing_path(wwise_banks_path)
        wwise_project    = settings.wwise_project
        wwise_cli        = os.path.join(os.getenv('WWISEROOT'),  "Authoring\\x64\\Release\\bin\\WWiseCLI.exe")
        wwise_command    = [wwise_cli,
                            os.path.abspath(wwise_project),
                            "-GenerateSoundBanks",
                            "-Platform",
                            arguments.platform]

        result = True
        with PerforceTransaction(cl_name,
                                 wwise_banks_path,
                                 workspace = workspace,
                                 submit_on_success = arguments.checkin) as transaction:
            if not call_process(".", wwise_command):
                result = False
                log_error("Error while running WwiseCli")
                transaction.abort()

        return result
