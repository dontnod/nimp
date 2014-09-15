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
    # __init__
    def __init__(self):
        Module.__init__(self, "configuration", [])

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):
        log_group = parser.add_argument_group("Configuration")

        return True

    #---------------------------------------------------------------------------
    # load
    def load(self, context):
        parser      = argparse.ArgumentParser(formatter_class=argparse.HelpFormatter)
        return _load_settings(context) and _load_arguments(context, parser)

#---------------------------------------------------------------------------
# _read_config_file
def _read_config_file(filename):
    try:
        locals = {}
        exec(compile(open(filename, "rb").read(), filename, 'exec'), None, locals)
        if locals.has_key("config"):
            return locals["config"]
        log_error("Configuration file {0} has no 'config' section.", filename)
    except Exception as e:
        log_error("Unable to load configuration file {0}: {1}", filename, str(e))
    return {}

#---------------------------------------------------------------------------
# _load_settings
def _load_settings(context):
    class Settings:
        pass

    global_settings = _read_config_file("nimp.conf")

    settings = Settings()
    for key, value in global_settings.items():
        setattr(settings, key, value)
    setattr(context, 'settings', settings)

    return True

#---------------------------------------------------------------------------
# _load_arguments
def _load_arguments(context, parser):
    modules     = context.modules

    for module in modules:
        if hasattr(module, "configure_arguments"):
            if( not module.configure_arguments(context, parser)):
                return False

    local_configuration_file_name = os.path.join(get_settings_directory(), "Dne/pytools_local_settings.conf")
    log_verbose("Loading config file {0}", local_configuration_file_name)
    parser.set_defaults(*_read_config_file(local_configuration_file_name))

    (arguments, unknown_args) = parser.parse_known_args()
    setattr(arguments, "unknown_args", unknown_args)
    setattr(context, 'arguments', arguments)
    return True

