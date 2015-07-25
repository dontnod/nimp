# -*- coding: utf-8 -*-

import os.path
import shutil

from nimp.utilities.perforce import *
from nimp.utilities.processes import *
from nimp.utilities.file_mapper import *
from nimp.utilities.deployment import *
from nimp.utilities.system import *

#---------------------------------------------------------------------------
def build_wwise_banks(env):
    """ Builds and optionnaly submits banks. Following attributes should be
        defined on env :
        platform            : The platform to build banks for.
        wwise_banks_path    : Relative path to the directory to checkout and
                              eventually submit (*.bnk files directory).
        wwise_project       : Relative path of the WWise project to build.
        checkin             : True to commit built banks, False otherwise."""
    platform         = env.platform
    wwise_project    = env.wwise_project
    wwise_banks_path = os.path.join(env.wwise_banks_path, env.wwise_banks_platform)
    cl_description   = "[CIS] Updated {0} WWise banks from changelist {1}".format(platform, p4_get_last_synced_changelist())
    wwise_cli_path   = os.path.join(os.getenv('WWISEROOT'), "Authoring/x64/Release/bin/WWiseCLI.exe")

    # WWiseCLI doesn’t handle Unix path separators properly
    if is_msys():
        wwise_project = wwise_project.replace('/', '\\')

    wwise_command = [wwise_cli_path,
                     wwise_project,
                     "-GenerateSoundBanks",
                     "-Platform",
                     env.wwise_cmd_platform]

    with p4_transaction(cl_description, submit_on_success = env.checkin) as trans:
        log_notification(log_prefix() + "Checking out banks…")
        banks_files = env.map_files()
        banks_files.src(wwise_banks_path).recursive().files()
        if not all_map(checkout(trans), banks_files()):
            log_error(log_prefix() + "Errors occurred while checking out banks, aborting…")
            return False
        if call_process(".", wwise_command, stdout_callback = _wwise_log_callback) == 1:
            log_error(log_prefix() + "Error while running WWiseCLI…")
            trans.abort()
            return False

        log_notification(log_prefix() + "Adding created banks to Perforce…")
        return all_map(checkout(trans), banks_files())

#---------------------------------------------------------------------------
def _wwise_log_callback(line, default_log_function):
    """ WWiseCLI output callback to log as error specific output. """
    if "Fatal Error" in line:
        log_error(line)
    else:
        default_log_function(line)

