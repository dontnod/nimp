# -*- coding: utf-8 -*-

import argparse
import time

from    nimp.modules.module          import *

from    nimp.utilities.logging       import *
from    nimp.utilities.paths         import *

#-------------------------------------------------------------------------------
class ConfigurationModule(Module):
    #---------------------------------------------------------------------------
    def __init__(self):
        Module.__init__(self, "configuration", [])

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        log_group = parser.add_argument_group("Configuration")

        return True

    #---------------------------------------------------------------------------
    def load(self, context):
        parser      = argparse.ArgumentParser(formatter_class=argparse.HelpFormatter)
        return _load_settings(context) and _load_arguments(context, parser)

#---------------------------------------------------------------------------
def _load_settings(context):
    while not os.path.exists(".nimp.conf") and os.path.abspath(os.sep) != os.getcwd():
        os.chdir("..")

    if not os.path.isfile(".nimp.conf"):
        log_error("Unable to find a .nimp.conf config file in current or parents directories.")
        return False;

    context.load_config_file(".nimp.conf")

    return True

#---------------------------------------------------------------------------
def _load_arguments(context, parser):
    modules     = context.modules

    for module in modules:
        if hasattr(module, "configure_arguments"):
            if( not module.configure_arguments(context, parser)):
                return False

    (arguments, unknown_args) = parser.parse_known_args()
    setattr(context, "unknown_args", unknown_args)

    for key, value in vars(arguments).items():
        setattr(context, key, value)

    context.standardize_names()
    return True
