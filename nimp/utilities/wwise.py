# -*- coding: utf-8 -*-

import os.path

from nimp.utilities.perforce  import *
from nimp.utilities.processes import *
from nimp.utilities.file_set  import *
import shutil

def wwise_cache_platform(platform):
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

def wwise_banks_platform(platform):
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
        "dingo"         : "X360",
        "xboxone"       : "X360",
        "orbis"         : "PS4",
        "ps4"           : "ps4"}[platform.lower()]

def wwise_cmd_line_platform(platform):
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

def build_wwise_banks(context):
    platform         = context.platform
    wwise_banks_path = context.wwise_banks_path
    wwise_banks_path = os.path.join(wwise_banks_path, wwise_banks_platform(platform))
    cl_name          = "[CIS] Updated {0} Wwise Banks".format(platform)
    wwise_cli_path   = os.path.join(os.getenv('WWISEROOT'), "Authoring\\x64\\Release\\bin\\WWiseCLI.exe")
    wwise_command    = [wwise_cli_path,  os.path.abspath(context.wwise_project), "-GenerateSoundBanks", "-Platform", wwise_cmd_line_platform(platform)]

    log_notification("Updating local Wwise cache...")
    _copy_wwise_cache(context, context.shared_cache_path, context.local_cache_path)

    result      = True
    with p4_transaction(cl_name, submit_on_success = context.checkin) as trans:
        log_notification("Checking out bank files...")
        add_to_p4(context, trans, wwise_banks_path)
        if call_process(".", wwise_command) == 1:
            result = False
            log_error("Error while running WwiseCli...")
            trans.abort()
        else:
            log_notification("Adding bank files to perforce...")
            add_to_p4(context, trans, wwise_banks_path)
            log_notification("Updating shared Wwise cache...")
            _copy_wwise_cache(context, context.local_cache_path, context.shared_cache_path)

    return result

def _copy_wwise_cache(context, source, destination):
    wwise_cache = copy_files(context).frm(source).newer().to(destination)
    wwise_cache = wwise_cache.format(platform = wwise_cache_platform(context.platform))
    log_notification("Listing cache files...")
    wwise_cache = wwise_cache.recursive().add('*')
    log_notification("Copying needed files...")
    wwise_cache.process(copy_mkdest_dir)