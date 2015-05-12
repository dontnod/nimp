# -*- coding: utf-8 -*-

import os.path
import shutil

from nimp.utilities.perforce import *
from nimp.utilities.processes import *
from nimp.utilities.file_mapper import *
from nimp.utilities.deployment import *

#---------------------------------------------------------------------------
def build_wwise_banks(env):
    """ Builds and optionnaly submits banks. Following attributes should be
        defined on env:
        platform         : The platform to build banks for.
        wwise.banks_path : Relative path to the directory to checkout and
                           eventually submit (*.bnk files directory).
        wwise.project    : Relative path of the WWise project to build.
        checkin          : True to commit built banks, False otherwise."""
    platform         = env.platform
    wwise_project    = env.wwise['project']
    wwise_banks_path = os.path.join(env.wwise['banks_path'], env.wwise_banks_platform)
    cl_name          = "[CIS] Updated {0} WWise Banks from CL {1}".format(platform, p4_get_last_synced_changelist())
    wwise_cli_path   = os.path.join(os.getenv('WWISEROOT'), "Authoring/x64/Release/bin/WWiseCLI.exe")

    # WWiseCLI doesn’t handle Unix path separators properly
    if os.environ.get('MSYSTEM') == 'MSYS':
        wwise_project = wwise_project.replace('/', '\\')

    # One of the WWise tools doesn’t like duplicate environment variables;
    # we remove any uppercase version we find. The loop is O(n²) but we
    # don’t have that many entries so it’s all right.
    env_vars = [x.upper() for x in os.environ.keys()]
    for dupe in set([x for x in env_vars if env_vars.count(x) > 1]):
        del os.environ[dupe]

    wwise_command = [wwise_cli_path,
                     wwise_project,
                     "-GenerateSoundBanks",
                     "-Platform",
                     env.wwise_cmd_platform]

    with p4_transaction(cl_name, submit_on_success = env.checkin) as trans:
        log_notification("[nimp] Checking out banks…")
        banks_files = env.map_files()
        banks_files.src(wwise_banks_path).recursive().files()
        if not all_map(checkout(trans), banks_files()):
            log_error("[nimp] Errors occurred while checking out banks, aborting…")
            return False
        if call_process(".", wwise_command, log_callback = _wwise_log_callback) == 1:
            log_error("[nimp] Error while running WWiseCLI…")
            trans.abort()
            return False

        log_notification("[nimp] Adding created banks to Perforce…")
        return all_map(checkout(trans), banks_files())

#---------------------------------------------------------------------------
def _wwise_log_callback(line, default_log_function):
    """ WWiseCLI output callback to log as error specific output. """
    if "Fatal Error" in line:
        log_error(line)
    else:
        default_log_function(line)

