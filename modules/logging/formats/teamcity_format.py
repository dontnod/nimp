# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
from modules.logging.format     import *

from utilities.logging          import *

#-------------------------------------------------------------------------------
# TeamcityFormat
#-------------------------------------------------------------------------------
class TeamcityFormat(Format):

    #---------------------------------------------------------------------------
    # __init__
    def __init__(self):
        Format.__init__(self, "teamcity")

    #---------------------------------------------------------------------------
    # format_message
    def format_message(self, log_level, message_format, *args):
        message_text = message_format.format(*args)
        if log_level == LOG_LEVEL_NOTIFICATION or log_level == LOG_LEVEL_VERBOSE:
            return message_text + '\n'
        else:
            message_text = message_text.replace("|", "||")
            message_text = message_text.replace("\n", "|n")
            message_text = message_text.replace("\r", "")
            message_text = message_text.replace("'", "|'")
            message_text = message_text.replace("[", "|[")
            message_text = message_text.replace("]", "|]")
            if log_level == LOG_LEVEL_WARNING:
                return "##teamcity[message text='" + message_text + "' status='WARNING']\n"
            if log_level == LOG_LEVEL_ERROR:
                return "##teamcity[message text='" + message_text + "' status='FAILURE']\n"
        assert(False)

    #---------------------------------------------------------------------------
    # start_progress
    def start_progress(self,
                       total,
                       position_formatter = None,
                       speed_formatter    = None,
                       total_formatter    = None,
                       template           = DEFAULT_BAR_TEMPLATE,
                       width              = DEFAULT_BAR_WIDTH):
        return None

    #---------------------------------------------------------------------------
    # update_progress
    def update_progress(self, value, step_name = None):
        return None

    #---------------------------------------------------------------------------
    # end_progress
    def end_progress(self):
        return None