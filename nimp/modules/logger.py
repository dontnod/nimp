import sys
import codecs

from nimp.utilities.logging import *

class Logger:
    #---------------------------------------------------------------------------
    def __init__(self, format, verbose):
        self._stdout = codecs.getwriter('cp437')(sys.stdout)
        self._stderr = codecs.getwriter('cp437')(sys.stderr)
        self._format = format
        self._verbose = verbose

    #---------------------------------------------------------------------------
    def log_message(self, log_level, message_format, *args):
        formatted_message = self._format.format_message(log_level, message_format, *args)
        if log_level != LOG_LEVEL_VERBOSE or self._verbose:
            if log_level == LOG_LEVEL_ERROR or log_level == LOG_LEVEL_WARNING:
                sys.stderr.write(formatted_message)
                sys.stderr.flush()
            else:
                sys.stdout.write(formatted_message)
                sys.stdout.flush()

    #---------------------------------------------------------------------------
    def start_progress(self,
                       total,
                       position_formatter,
                       speed_formatter,
                       total_formatter,
                       step_name_formatter,
                       template,
                       width):
        self._format.start_progress(total               = total,
                                    position_formatter  = position_formatter,
                                    speed_formatter     = speed_formatter,
                                    total_formatter     = total_formatter,
                                    step_name_formatter = step_name_formatter,
                                    template            = template,
                                    width               = width)

    #---------------------------------------------------------------------------
    def update_progress(self, value, step_name = None):
        progress_string = self._format.update_progress(value, step_name)
        if progress_string is not None:
            sys.stdout.write(progress_bar_string)
            sys.stdout.flush()

    #---------------------------------------------------------------------------
    def end_progress(self):
        end_progress = self._format.end_progress()
        sys.stdout.write(end_progress)
        sys.stdout.flush()

