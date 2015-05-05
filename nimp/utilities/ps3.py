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
        if 0 != call_process(pkg_destination, ["make_package_npdrm", pkg_conf_file, pkg_source]):
            log_error("Error running make_package_npdrm")
            return False

    return True
