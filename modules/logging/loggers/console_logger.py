# -*- coding: utf-8 -*-

import sys

from modules.logging.logger     import *

#-------------------------------------------------------------------------------
class ConsoleLogger(Logger):
    def __init__(self):
        Logger.__init__(self, "console")

    #---------------------------------------------------------------------------
    def log_formatted_message(self, log_level, formatted_message):
        if log_level != LOG_LEVEL_VERBOSE or self.verbose() is True:
            if log_level == LOG_LEVEL_ERROR or log_level == LOG_LEVEL_WARNING:
                sys.stderr.write(formatted_message)
                sys.stderr.flush()
            else:
                sys.stdout.write(formatted_message)
                sys.stdout.flush()

    #---------------------------------------------------------------------------
    def _print_progress_bar(self, progress_bar_string):
        sys.stdout.write(progress_bar_string)
        sys.stdout.flush()
