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
    vcxproj = 'Engine/Intermediate/ProjectFiles/' + env.game + '.vcxproj'

    return _ue4_build_project(env.solution, vcxproj, env.ue4_build_platform,
                              env.configuration, env.vs_version, 'Build')

#---------------------------------------------------------------------------
def _ue4_build_project(sln_file, project, build_platform, configuration, vs_version, target = 'Rebuild'):
    return vsbuild(sln_file, build_platform, configuration, project, vs_version, target)

