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

    if not env.configuration:
        log_error(log_prefix() + "Invalid empty value for configuration")
        return False

    if _ue4_generate_project() != 0:
        log_error(log_prefix() + "Error generating UE4 project files")
        return False

    if env.ue4_build_platform == 'PS4':
        if not _ue4_build_project(env.solution, 'PS4MapFileUtil', 'Win64',
                                  env.configuration, vs_version, 'Build'):
            log_error(log_prefix() + "Could not build PS4MapFileUtil.exe")
            return False

    # The Durango XDK does not support Visual Studio 2013 yet
    if env.is_xone:
        vs_version = '11'

    return _ue4_build_project(env.solution, env.game, env.ue4_build_platform,
                              env.configuration, vs_version, 'Build')


#---------------------------------------------------------------------------
def _ue4_generate_project():

    return call_process('.', ['../GenerateProjectFiles.bat'])


#---------------------------------------------------------------------------
def _ue4_build_project(sln_file, project, build_platform,
                       configuration, vs_version, target = 'Rebuild'):

    return vsbuild(sln_file, build_platform, configuration,
                   project, vs_version, target)


#---------------------------------------------------------------------------
def ue4_commandlet(env, commandlet, *args):
    cmdline = [ "../Engine/Binaries/Win64/UE4Editor.exe",
                env.game,
                "-run=%s" % commandlet]

    cmdline += list(args)
    cmdline += ['-nopause', '-buildmachine', '-forcelogflush', '-unattended', '-noscriptcheck']

    return call_process(".", cmdline) == 0

