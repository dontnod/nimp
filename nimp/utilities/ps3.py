# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
import shutil

from nimp.utilities.build import *
from nimp.utilities.deployment import *
from nimp.utilities.system import *


#-------------------------------------------------------------------------------
def ps3_generate_pkgs(env, source, destination):
    packages_config = env.packages_config

    if hasattr(packages_config, "__call__"):
        packages_config = packages_config(env)
    else:
        packages_config = packages_config[env.dlc]

    for package in packages_config:
        pkg_destination = env.format(destination, pkg_dest = package['pkg_dest'])
        pkg_source      = env.format(os.path.join(source, package['source']))
        pkg_conf_file   = env.format(os.path.join(source, package['conf']))
        safe_makedirs(pkg_destination)

        if('drm_files' in package):
            for drm_source, drm_dest in package['drm_files'].items():
                drm_source = env.format(drm_source)
                drm_dest = env.format(drm_dest)
                drm_source = os.path.join(pkg_source, drm_source)
                drm_dest = os.path.join(pkg_source, drm_dest)
                drm_source = drm_source.replace('/', '\\')
                drm_dest = drm_dest.replace('/', '\\')
                if call_process('.', ['make_edata_npdrm', drm_source, drm_dest]) != 0:
                    return False
        # make_package_npdrm doesn’t handle Unix path separators properly
        if is_msys():
            pkg_conf_file = pkg_conf_file.replace('/', '\\')

        if 0 != call_process(pkg_destination, ["make_package_npdrm", pkg_conf_file, pkg_source]):
            log_error(log_prefix() + "Error running make_package_npdrm")
            return False

    return True
