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
    vcxproj    = 'Engine/Intermediate/ProjectFiles/' + env.game + '.vcxproj'

    if _ue4_generate_project() != 0:
        log_error("Error generating UE4 project files")
        return False

    if env.ue4_build_platform == 'PS4':
        ps4_vcxproj = 'Engine/Intermediate/ProjectFiles/PS4MapFileUtil.vcxproj'
        if not _ue4_build_project(env.solution, ps4_vcxproj, 'Win64',
                                  env.configuration, vs_version, 'Build'):
            log_error("Could not build PS4MapFileUtil.exe")
            return False

    return _ue4_build_project(env.solution, vcxproj, env.ue4_build_platform,
                              env.configuration, vs_version, 'Build')

#---------------------------------------------------------------------------
def _ue4_generate_project():
    return call_process('.', ['./GenerateProjectFiles.bat'])

#---------------------------------------------------------------------------
def _ue4_build_project(sln_file, project, build_platform, configuration, vs_version, target = 'Rebuild'):
    return vsbuild(sln_file, build_platform, configuration, project, vs_version, target)

