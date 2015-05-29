# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
import shutil
import os

from nimp.utilities.build import *
from nimp.utilities.deployment import *

#---------------------------------------------------------------------------
def ue4_build(env):
    vs_version = '12'

    if _ue4_generate_project() != 0:
        log_error("[nimp] Error generating UE4 project files")
        return False

    if env.ue4_build_platform == 'PS4':
        if not _ue4_build_project(env.solution, 'PS4MapFileUtil', 'Win64',
                                  env.configuration, vs_version, 'Build'):
            log_error("[nimp] Could not build PS4MapFileUtil.exe")
            return False

    return _ue4_build_project(env.solution, env.game, env.ue4_build_platform,
                              env.configuration, vs_version, 'Build')

#---------------------------------------------------------------------------
def _ue4_generate_project():
    return call_process('.', ['../GenerateProjectFiles.bat'])

#---------------------------------------------------------------------------
def _ue4_build_project(sln_file, project, build_platform, configuration, vs_version, target = 'Rebuild'):
    return vsbuild(sln_file, build_platform, configuration, project, vs_version, target)

#---------------------------------------------------------------------------
def ue4_commandlet(env):
    cmdline = [ "../Engine/Binaries/Win64/UE4Editor.exe",
               env.game,
               "-run",
               env.commandlet]

    if(env.arg is not None):
        for key_value in env.arg:
            cmdline += [key_value[0], key_value[1]]
    cmdline += ['-nopause', '-buildmachine', '-forcelogflush', '-unattended', '-noscriptcheck']

    return call_process(".", cmdline) == 0