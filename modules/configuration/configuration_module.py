# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# imports
#-------------------------------------------------------------------------------
import argparse
import time

from    modules.module          import *

from    utilities.files         import *
from    utilities.logging       import *
from    utilities.paths         import *

#-------------------------------------------------------------------------------
# CMakeModule
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

    load_config_file(".nimp.conf", context)

    return True

#---------------------------------------------------------------------------
def _load_arguments(context, parser):
    modules     = context.modules

    for module in modules:
        if hasattr(module, "configure_arguments"):
            if( not module.configure_arguments(context, parser)):
                return False

    (arguments, unknown_args) = parser.parse_known_args()
    setattr(arguments, "unknown_args", unknown_args)
    setattr(context, 'arguments', arguments)
    return True

#---------------------------------------------------------------------------
def load_config_file(filename, context):
    class Settings:
        pass

    settings         = Settings()
    settings_content = read_config_file(filename)

    if(settings_content is None):
        return False

    for key, value in settings_content.items():
        setattr(settings, key, value)

    setattr(context, 'settings', settings)
    return True

#---------------------------------------------------------------------------
def read_config_file(filename):
    try:
        conf = open(filename, "rb").read()
    except Exception as exception:
        log_error("Unable to open configuration file : {0}", exception)
        return None
    # Parse configuration file
    try:
        locals = {}
        exec(compile(conf, filename, 'exec'), None, locals)
        if "config" in locals:
            return locals["config"]
        log_error("Configuration file {0} has no 'config' section.", filename)
    except Exception as e:
        log_error("Unable to load configuration file {0}: {1}", filename, str(e))

    return {}
