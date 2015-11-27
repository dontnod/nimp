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
def ps3_generate_edata(env, source):
    if not env.check_keys('packages_config_file'):
        log_error("No packages config file defined in env")
        return False

    package_config_file = env.format(env.packages_config_file)

    if not env.load_config_file(package_config_file):
        log_error("Unable to load packages config")
        return False

    packages_config = env.packages_config
    if hasattr(packages_config, "__call__"):
        packages_config = packages_config(env)
    else:
        packages_config = packages_config[env.dlc]

    for package in packages_config:
        pkg_source      = env.format(os.path.join(source, package['source']))
        pkg_conf_file   = env.format(os.path.join(source, package['conf']))

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
    return True

#-------------------------------------------------------------------------------
def ps3_generate_pkgs(env, source, destination):
    packages_config = env.packages_config

    if hasattr(packages_config, "__call__"):
        packages_config = packages_config(env)
    else:
        packages_config = packages_config[env.dlc]

    for package in packages_config:
        pkg_destination = env.format(os.path.join(destination, package['pkg_dest']))
        pkg_source      = env.format(os.path.join(source, package['source']))
        pkg_conf_file   = env.format(os.path.join(source, package['conf']))
        safe_makedirs(pkg_destination)

        # make_package_npdrm doesn’t handle Unix path separators properly
        if is_msys():
            pkg_conf_file = pkg_conf_file.replace('/', '\\')

        if call_process(pkg_destination,
                        [ "make_package_npdrm", pkg_conf_file, pkg_source ],
                        heartbeat = 30) != 0:
            log_error("Error running make_package_npdrm")
            return False

    return True
