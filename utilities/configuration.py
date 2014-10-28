# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# imports
#-------------------------------------------------------------------------------
from utilities.logging  import *

#---------------------------------------------------------------------------
def check_config_value(settings, option_name):
    if not hasattr(settings, option_name):
        log_error("Unable to find option {0} in config. Please set it", option_name)
        return False

    return True
