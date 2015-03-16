# -*- coding: utf-8 -*-

import os.path
import shutil

from nimp.utilities.perforce    import *
from nimp.utilities.processes   import *
from nimp.utilities.file_mapper import *

#---------------------------------------------------------------------------
def build_wwise_banks(context):
    """ Builds and optionnaly submits banks. Following attributes should be
        defined on context :
        platform            : The platform to build banks for.
        wwise_banks_path    : Relative path to the directory to checkout and
                              eventually  submit (*.bnk files directory).
        wwise_project       : Relative path of the Wwise project to build.
        checkin             : True to commit built banks, False otherwise."""
    load_wwise_context(context)
    platform         = context.platform
    wwise_banks_path = context.wwise_banks_path
    wwise_banks_path = os.path.join(wwise_banks_path, context.wwise_banks_platform)
    cl_name          = "[CIS] Updated {0} Wwise Banks from CL {1}".format(platform,  p4_get_last_synced_changelist())
    wwise_cli_path   = os.path.join(os.getenv('WWISEROOT'), "Authoring\\x64\\Release\\bin\\WWiseCLI.exe")
    wwise_command    = [wwise_cli_path,
                        os.path.abspath(context.wwise_project),
                        "-GenerateSoundBanks",
                        "-Platform",
                        context.wwise_cmd_platform]

    with p4_transaction(cl_name, submit_on_success = context.checkin) as trans:
        log_notification("Checking out banks...")
        checkout_banks = map_sources(trans.add, vars(context)).once().files().recursive().frm(wwise_banks_path)
        if not all(checkout_banks()):
            log_error("Errors occured while checking out banks, aborting...")
            return False
        if call_process(".", wwise_command, log_callback = _wwise_log_callback) == 1:
            log_error("Error while running WwiseCli...")
            trans.abort()
            return False

        log_notification("Adding created banks to perforce...")
        return all(checkout_banks())

#---------------------------------------------------------------------------
def _wwise_log_callback(line, default_log_function):
    """ WwiseCli output callback to log as error specific output. """
    if "Fatal Error" in line:
        log_error(line)
    else:
        default_log_function(line)
