# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# imports
#-------------------------------------------------------------------------------
import argparse
import time

from    modules.module          import *

from    utilities.files         import *
from    utilities.json_file     import *
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
# _load_workspace_settings
def _load_settings(context):
    class Settings:
        pass

    json_settings = read_json("settings.json")

    if json_settings is None:
        log_error("Unable to load json settings.")
        return False

    settings = Settings()
    for key, value in json_settings.items():
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


    local_configuration_file_name = os.path.join(get_settings_directory(), "Dne/pytools_local_settings.json")
    log_verbose("Loading config file {0}", local_configuration_file_name)
    json_configuration = read_json(local_configuration_file_name)

    if json_configuration is not None:
        parser.set_defaults(**json_configuration)
        log_verbose("Default configuration loaded")
    else:
        log_verbose("Can't parse repository configuration file {0}. Default configuration will be used.", local_configuration_file_name)

    (arguments, unknown_args) = parser.parse_known_args()
    setattr(arguments, "unknown_args", unknown_args)
    setattr(context, 'arguments', arguments)
    return True
