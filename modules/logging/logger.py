# -*- coding: utf-8 -*-

from utilities.logging              import *

#-------------------------------------------------------------------------------
class Logger:
    #---------------------------------------------------------------------------
    def __init__(self, name):
        self._name    = name
        self._format  = None
        self._verbose = False

    #---------------------------------------------------------------------------
    def name(self):
        return self._name

    #---------------------------------------------------------------------------
    def initialize(self, format, context, verbose):
        self._format  = format
        self._verbose = verbose

    #---------------------------------------------------------------------------
    def verbose(self):
        return self._verbose

    #---------------------------------------------------------------------------
    def log_message(self, log_level, message_format, *args):
        formatted_message = self._format.format_message(log_level, message_format, *args)
        self.log_formatted_message(log_level, formatted_message)

    #---------------------------------------------------------------------------
    def start_progress(self,
                       total,
                       position_formatter,
                       speed_formatter,
                       total_formatter,
                       template,
                       width):
        self._format.start_progress(total               = total,
                                    position_formatter  = position_formatter,
                                    speed_formatter     = speed_formatter,
                                    total_formatter     = total_formatter,
                                    template            = template,
                                    width               = width)

    #---------------------------------------------------------------------------
    def update_progress(self, value, step_name = None):
        progress_string = self._format.update_progress(value, step_name)
        if progress_string is not None:
            self._print_progress_bar(progress_string)

    #---------------------------------------------------------------------------
    def end_progress(self):
        end_progress = self._format.end_progress()
        self._print_progress_bar(end_progress)

    #---------------------------------------------------------------------------
    def log_formatted_message(self, log_level, formatted_message):
        assert(False)

    #---------------------------------------------------------------------------
    def _print_progress_bar(self, progress_bar_string):
        assert(False)

