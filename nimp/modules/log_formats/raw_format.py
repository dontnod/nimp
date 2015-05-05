# -*- coding: utf-8 -*-

import os
import  sys

from nimp.modules.log_formats.format import *
from nimp.modules.log_formats.standard_progress_bar import *
from nimp.utilities.logging import *

#-------------------------------------------------------------------------------
class RawFormat(Format):
    #---------------------------------------------------------------------------
    def __init__(self):
        Format.__init__(self, "raw")
        self._total = 0
        self._step_name_formatter = None

    #---------------------------------------------------------------------------
    def format_message(self, log_level, message_format, *args):
        formatted_message = message_format.format(*args) + "\n"
        current_directory = os.getcwd()
        if (log_level == LOG_LEVEL_NOTIFICATION or log_level == LOG_LEVEL_VERBOSE) or log_level == LOG_LEVEL_WARNING or log_level == LOG_LEVEL_ERROR:
            return formatted_message
        return None

    #---------------------------------------------------------------------------
    def start_progress(self,
                       total,
                       position_formatter  = None,
                       speed_formatter     = None,
                       total_formatter     = None,
                       step_name_formatter = None,
                       template            = DEFAULT_BAR_TEMPLATE,
                       width               = DEFAULT_BAR_WIDTH):
        self._total = total
        self._step_name_formatter = step_name_formatter
        pass

    #---------------------------------------------------------------------------
    def update_progress(self, value, step_name = None):
        formatter = self._step_name_formatter
        step_name = step_name if formatter is None else formatter(step_name)
        log_verbose("{0}/{1} : {2}", value, self._total, step_name)

    #---------------------------------------------------------------------------
    def end_progress(self):
        self._total = 0
        self._step_name_formatter = None
        return ""
