# -*- coding: utf-8 -*-

from datetime import date

import os
import io
import stat
import os.path
import tempfile;
import shutil
import stat
import glob
import fnmatch
import re
import contextlib
import pathlib

from nimp.utilities.processes import *
from nimp.utilities.ps3 import *
from nimp.utilities.ps4 import *

#---------------------------------------------------------------------------
def generate_pkg_config(env, loose_files_dir = None):
    if(env.is_win32):
        return True

    if not _load_package_config(env):
        return False

    loose_files_dir = loose_files_dir or env.publish_ship
    if env.is_ps4:
        return generate_gp4(env, loose_files_dir)

    return True

#---------------------------------------------------------------------------
def make_packages(env, source = None, destination = None):
    if(env.is_win32):
        return True

    source = source or env.publish_ship
    destination = destination or env.publish_pkgs

    if not _load_package_config(env):
        return False

    if env.is_ps3:
        return ps3_generate_pkgs(env, source, destination)
    elif env.is_ps4:
        ps4_generate_pkgs(env, source, destination)
    return True

#---------------------------------------------------------------------------
def _load_package_config(env):
    if not env.check_keys('packages_config_file'):
        return False

    package_config = env.format(env.packages_config_file)

    if not env.load_config_file(package_config):
        return False
    return True
