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
    source          = context.format(source)
    pkg_conf_file   = os.path.join(source, "pkg.config")

    if not context.load_config_file(pkg_conf_file):
        log_error("Unable to load pkgs config file")
        return False

    for name, config in context.ps3_pkgs.items():
        pkg_destination = context.format(destination, pkg_name = name)
        pkg_source      = os.path.join(source, config['source'])
        pkg_conf_file   = os.path.join(source, config['conf'])
        if not os.path.exists(pkg_destination):
            os.makedirs(pkg_destination)
        if 0 != call_process(pkg_destination, ["make_package_npdrm", pkg_conf_file, pkg_source]):
            log_error("Error running make_package_npdrm")
            return False

    return True