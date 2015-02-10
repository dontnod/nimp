# -*- coding: utf-8 -*-

import os.path

from utilities.perforce  import *
from utilities.processes import *


def build_wwise_banks(platform, wwise_banks_path, wwise_project, checkin = False):
    platform_dir     = platform if platform.lower() != "xbox360" else "X360"
    wwise_banks_path = os.path.join(wwise_banks_path, platform_dir)
    cl_name          = "[CIS] Updated {0} Wwise Banks".format(platform)
    wwise_cli_path   = os.path.join(os.getenv('WWISEROOT'), "Authoring\\x64\\Release\\bin\\WWiseCLI.exe")
    wwise_command    = [wwise_cli_path,
                        os.path.abspath(wwise_project),
                        "-GenerateSoundBanks",
                        "-Platform",
                        platform]

    result = True
    with PerforceTransaction(cl_name, wwise_banks_path, submit_on_success = checkin) as transaction:
        if not call_process(".", wwise_command):
            result = False
            log_error("Error while running WwiseCli")
            transaction.abort()

    return result
