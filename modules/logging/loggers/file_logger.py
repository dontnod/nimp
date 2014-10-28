# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
import datetime
import os

from modules.logging.logger         import *

#-------------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------------
LOGS_PATH                       = "Logs"
CHGR_PY_LOG_PATH                = "Chgr.py"
CHGR_PY_LOG_FILE_NAME_TEMPLATE  = "chgr_py_{year}_{month}_{day}_{hour}_{minute}_{microsecond}.log"

#-------------------------------------------------------------------------------
# FileLogger
#-------------------------------------------------------------------------------
class FileLogger(Logger):
    #---------------------------------------------------------------------------
    # __init__
    def __init__(self):
        Logger.__init__(self, "file")
        self._log_file = None

    #---------------------------------------------------------------------------
    def initialize(self, format, context, verbose):
        Logger.initialize(self, format, context, verbose)
        configuration       = context.configuration
        logs_path           = os.path.join(configuration.local_directory, LOGS_PATH)
        chgr_py_logs_path   = os.path.join(logs_path, CHGR_PY_LOG_PATH)
        now                 = datetime.datetime.now()
        log_file_name       = CHGR_PY_LOG_FILE_NAME_TEMPLATE.format(year        = now.year,
                                                                    month       = now.month,
                                                                    day         = now.day,
                                                                    hour        = now.hour,
                                                                    minute      = now.minute,
                                                                    microsecond = now.microsecond)
        log_file_path       = os.path.join(chgr_py_logs_path, log_file_name)

        if not os.path.exists(chgr_py_logs_path):
            os.makedirs(chgr_py_logs_path)
        try:
            self._log_file = open(log_file_path, "w")

        except IOError as io_error:
            pass
        if(self._log_file is None):
            print("Error while opening log file {0}".format(log_file_path))

    #---------------------------------------------------------------------------
    def log_formatted_message(self, log_level, formatted_message):
        if self._log_file is not None:
            self._log_file.write(formatted_message)

    #---------------------------------------------------------------------------
    # print_progress_bar
    def _log_formatted_message(self, log_level, formatted_message):
        if self._log_file is not None:
            self._log_file.write(formatted_message)
            self._log_file.write("\n")

    #---------------------------------------------------------------------------
    # _print_progress_bar
    def _print_progress_bar(self, progress_bar_string):
        pass