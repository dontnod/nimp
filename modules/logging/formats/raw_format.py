# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import os
import  sys

from modules.logging.format                         import *
from modules.logging.formats.standard_progress_bar  import *
from utilities.logging                              import *

#-------------------------------------------------------------------------------
class RawFormat(Format):

    #---------------------------------------------------------------------------
    def __init__(self):
        Format.__init__(self, "raw")
        self._progress_bar = None

    #---------------------------------------------------------------------------
    def format_message(self, log_level, message_format, *args):
        formatted_message = message_format.format(*args) + "\n"
        current_directory = os.getcwd()
        formatted_message = formatted_message.replace("../../../../..", current_directory)
        if (log_level == LOG_LEVEL_NOTIFICATION or log_level == LOG_LEVEL_VERBOSE) or log_level == LOG_LEVEL_WARNING or log_level == LOG_LEVEL_ERROR:
            return formatted_message
        return None

    #---------------------------------------------------------------------------
    def start_progress(self,
                       total,
                       position_formatter = None,
                       speed_formatter    = None,
                       total_formatter    = None,
                       template           = DEFAULT_BAR_TEMPLATE,
                       width              = DEFAULT_BAR_WIDTH):
        assert(self._progress_bar is None)
        self._progress_bar = StandardProgressBar(total                  = total,
                                                 position_formatter     = position_formatter,
                                                 speed_formatter        = speed_formatter,
                                                 total_formatter        = total_formatter,
                                                 template               = template,
                                                 width                  = width)

    #---------------------------------------------------------------------------
    def update_progress(self, value, step_name = None):
        assert(self._progress_bar is not None)
        return self._progress_bar.update(value, step_name)

    #---------------------------------------------------------------------------
    def end_progress(self):
        assert(self._progress_bar is not None)
        self._progress_bar = None
        return "                                                                   \r"

