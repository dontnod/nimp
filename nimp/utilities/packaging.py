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

from nimp.utilities.processes  import *
from nimp.utilities.ps3        import *
from nimp.utilities.ps4        import *

#---------------------------------------------------------------------------
def generate_pkg_config(context, loose_files_dir = None):
    if not _load_package_config(context):
        return False

    loose_files_dir = loose_files_dir or context.cis_ship_directory
    if context.is_ps4:
        return generate_gp4(context, loose_files_dir)

    return True

#---------------------------------------------------------------------------
def make_packages(context, source = None, destination = None):
    source      = source or context.cis_ship_directory
    destination = destination or  context.cis_pkgs_directory

    if not _load_package_config(context):
        return False

    if context.is_ps3:
        return ps3_generate_pkgs(context, source, destination)
    elif context.is_ps4:
        ps4_generate_pkgs(context, source, destination)
    return True

#---------------------------------------------------------------------------
def _load_package_config(context):
    if not context.check_keys('packages_config_file'):
        return False

    package_config = context.format(context.packages_config_file)

    if not context.load_config_file(package_config):
        return False
    return True