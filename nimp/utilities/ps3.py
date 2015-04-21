# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
import shutil

from nimp.utilities.build        import *
from nimp.utilities.deployment   import *


#-------------------------------------------------------------------------------
def ps3_generate_pkgs(context, source, destination):
    packages_config = context.packages_config

    if hasattr(packages_config, "__call__"):
        packages_config = packages_config(context)
    else:
        packages_config = packages_config[context.dlc]

    for package in packages_config:
        pkg_destination = context.format(destination, pkg_dest = package['pkg_dest'])
        pkg_source      = os.path.join(source, package['source'])
        pkg_conf_file   = os.path.join(source, package['conf'])
        if not os.path.exists(pkg_destination):
            os.makedirs(pkg_destination)
        if 0 != call_process(pkg_destination, ["make_package_npdrm", pkg_conf_file, pkg_source]):
            log_error("Error running make_package_npdrm")
            return False

    return True