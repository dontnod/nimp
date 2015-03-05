# -*- coding: utf-8 -*-

import os.path

from nimp.utilities.perforce    import *
from nimp.utilities.processes   import *
from nimp.utilities.file_mapper import *
import shutil

#---------------------------------------------------------------------------
def wwise_cache_platform(platform):
    """ Returns the name used for this platform in the Wwise cache directory.
    """
    return {
        "pc"            : "Windows",
        "pcconsole"     : "Windows",
        "win32"         : "Windows",
        "win64"         : "Windows",
        "windows"       : "Windows",
        "ps3"           : "Ps3",
        "xbox 360"      : "XBox360",
        "xbox360"       : "XBox360",
        "x360"          : "XBox360",
        "dingo"         : "XboxOne",
        "xboxone"       : "XboxOne",
        "orbis"         : "PS4",
        "ps4"           : "ps4"}[platform.lower()]

#---------------------------------------------------------------------------
def wwise_banks_platform(platform):
    """ Returns the name used for this platform in commited *.bnk directories.
    """
    return {
        "pc"            : "PC",
        "pcconsole"     : "PC",
        "win32"         : "PC",
        "win64"         : "PC",
        "windows"       : "PC",
        "ps3"           : "Ps3",
        "xbox 360"      : "X360",
        "xbox360"       : "X360",
        "x360"          : "X360",
        "dingo"         : "XboxOne",
        "xboxone"       : "XboxOne",
        "orbis"         : "PS4",
        "ps4"           : "ps4"}[platform.lower()]

#---------------------------------------------------------------------------
def wwise_cmd_line_platform(platform):
    """ Returns the name used for this platform when dealing with Wwise command line.
    """
    return {
        "pc"            : "Windows",
        "pcconsole"     : "Windows",
        "win32"         : "Windows",
        "win64"         : "Windows",
        "windows"       : "Windows",
        "ps3"           : "Ps3",
        "xbox 360"      : "XBox360",
        "xbox360"       : "XBox360",
        "x360"          : "XBox360",
        "dingo"         : "XboxOne",
        "xboxone"       : "XboxOne",
        "orbis"         : "PS4",
        "ps4"           : "ps4"}[platform.lower()]

#---------------------------------------------------------------------------
def build_wwise_banks(context):
    """ Builds and optionnaly submits banks. Following attributes should be
        defined on context :
        platform            : The platform to build banks for.
        wwise_banks_path    : Relative path to the directory to checkout and
                              eventually  submit (*.bnk files directory).
        wwise_project       : Relative path of the Wwise project to build.
        checkin             : True to commit built banks, False otherwise."""
    platform         = context.platform
    wwise_banks_path = context.wwise_banks_path
    wwise_banks_path = os.path.join(wwise_banks_path, wwise_banks_platform(platform))
    cl_name          = "[CIS] Updated {0} Wwise Banks from CL {1}".format(platform,  p4_get_last_synced_changelist())
    wwise_cli_path   = os.path.join(os.getenv('WWISEROOT'), "Authoring\\x64\\Release\\bin\\WWiseCLI.exe")
    wwise_command    = [wwise_cli_path,
                        os.path.abspath(context.wwise_project),
                        "-GenerateSoundBanks",
                        "-Platform",
                        wwise_cmd_line_platform(platform)]

    result      = True
    with p4_transaction(cl_name, submit_on_success = context.checkin) as trans:
        log_notification("Checking out banks...")
        checkout_banks = map_sources(trans.add, vars(context)).once().files().recursive().frm(wwise_banks_path)
        if not all(checkout_banks()):
            log_error("Errors occured while checking out banks, aborting...")
            return False
        if call_process(".", wwise_command, log_callback = _wwise_log_callback) == 1:
            log_error("Error while running WwiseCli...")
            trans.abort()
            result = False
        else:
            log_notification("Adding created banks to perforce...")
            if not all(checkout_banks()):
                return False

    return result

#---------------------------------------------------------------------------
def _wwise_log_callback(line, default_log_function):
    """ WwiseCli output callback to log as error specific output. """
    if "Fatal Error" in line:
        log_error(line)
    else:
        default_log_function(line)
