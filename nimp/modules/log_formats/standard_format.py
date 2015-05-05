# -*- coding: utf-8 -*-

import os
import sys
import shutil

from nimp.modules.log_formats.format import *
from nimp.modules.log_formats.standard_progress_bar import *
from nimp.utilities.logging import *

#-------------------------------------------------------------------------------
class StandardFormat(Format):
    #---------------------------------------------------------------------------
    def __init__(self):
        Format.__init__(self, "standard")
        self._progress_bar = None

    #---------------------------------------------------------------------------
    def format_message(self, log_level, message_format, *args):
        width, height = shutil.get_terminal_size((80, 20))
        if log_level == LOG_LEVEL_NOTIFICATION or log_level == LOG_LEVEL_VERBOSE:
            result = message_format.format(*args)
        elif log_level == LOG_LEVEL_WARNING:
            result = "[ WARNING ] : " + message_format.format(*args)
        else:
            result = "[  ERROR  ] : " + message_format.format(*args)
        return result + "\n"

    #---------------------------------------------------------------------------
    def start_progress(self,
                       total,
                       position_formatter  = None,
                       speed_formatter     = None,
                       total_formatter     = None,
                       step_name_formatter = None,
                       template            = DEFAULT_BAR_TEMPLATE,
                       width               = DEFAULT_BAR_WIDTH):
        assert(self._progress_bar is None)
        self._progress_bar = StandardProgressBar(total               = total,
                                                 position_formatter  = position_formatter,
                                                 speed_formatter     = speed_formatter,
                                                 total_formatter     = total_formatter,
                                                 step_name_formatter = step_name_formatter,
                                                 template            = template,
                                                 width               = width)

    #---------------------------------------------------------------------------
    def update_progress(self, value, step_name = None):
        assert(self._progress_bar is not None)
        return self._progress_bar.update(value, step_name)

    #---------------------------------------------------------------------------
    def end_progress(self):
        assert(self._progress_bar is not None)
        self._progress_bar = None
        return "\r\n"

