# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
import sys

from modules.logging.logger     import *

#-------------------------------------------------------------------------------
# ConsoleAndFileLogger
#-------------------------------------------------------------------------------
class ConsoleLogger(Logger):
    def __init__(self):
        Logger.__init__(self, "console")

    #---------------------------------------------------------------------------
    # log_formatted_message
    def log_formatted_message(self, log_level, formatted_message):
        if log_level != LOG_LEVEL_VERBOSE or self.verbose() is True:
            sys.stdout.write(formatted_message)
            sys.stdout.flush()

    #---------------------------------------------------------------------------
    # _print_progress_bar
    def _print_progress_bar(self, progress_bar_string):
        sys.stdout.write(progress_bar_string)
        sys.stdout.flush()