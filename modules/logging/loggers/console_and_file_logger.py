# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
from modules.logging.logger                 import *
from modules.logging.loggers.console_logger import *
from modules.logging.loggers.file_logger    import *

#-------------------------------------------------------------------------------
# ConsoleAndFileLogger
#-------------------------------------------------------------------------------
class ConsoleAndFileLogger(Logger):
    def __init__(self):
        Logger.__init__(self, "console_and_file")
        self._console_logger = ConsoleLogger()
        self._file_logger    = FileLogger()

    #---------------------------------------------------------------------------
    # initialize
    def initialize(self, format, context, verbose):
        Logger.initialize(self, format, context, verbose)
        self._console_logger.initialize(format, context, verbose)
        self._file_logger.initialize(format, context, verbose)

    #---------------------------------------------------------------------------
    # log_formatted_message
    def log_formatted_message(self, log_level, formatted_message):
        self._console_logger.log_formatted_message(log_level, formatted_message)
        self._file_logger.log_formatted_message(log_level, formatted_message)

    #---------------------------------------------------------------------------
    # _print_progress_bar
    def _print_progress_bar(self, progress_bar_string):
        self._console_logger._print_progress_bar(progress_bar_string)
        self._file_logger._print_progress_bar(progress_bar_string)