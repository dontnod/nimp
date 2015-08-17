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
    wwise_project    = env.wwise_project
    wwise_cli_path   = os.path.join(os.getenv('WWISEROOT'), "Authoring/x64/Release/bin/WWiseCLI.exe")

    # WWiseCLI doesn’t handle Unix path separators properly
    if is_msys():
        wwise_project = wwise_project.replace('/', '\\')

    wwise_command = [wwise_cli_path,
                     wwise_project,
                     "-GenerateSoundBanks",
                     "-Platform",
                     env.wwise_cmd_platform]

    if call_process(".", wwise_command, stdout_callback = _wwise_log_callback) == 1:
        log_error(log_prefix() + "Error while running WWiseCLI…")
        return False

#---------------------------------------------------------------------------
def _wwise_log_callback(line, default_log_function):
    """ WWiseCLI output callback to log as error specific output. """
    if "Fatal Error" in line:
        log_error(line)
    else:
        default_log_function(line)

