# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Configuration
#-------------------------------------------------------------------------------
DEFAULT_BAR_TEMPLATE = "{label}[{filled_chars}{empty_chars}] {position}/{total} - {time_left} - {speed}"
DEFAULT_BAR_WIDTH    = 15

#-------------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------------
LOG_LEVEL_VERBOSE       = 1
LOG_LEVEL_NOTIFICATION  = 2
LOG_LEVEL_WARNING       = 3
LOG_LEVEL_ERROR         = 4

#-------------------------------------------------------------------------------
# Globals
#-------------------------------------------------------------------------------
g_logger = None # monkey patch spotted

#-------------------------------------------------------------------------------
# log_message
#-------------------------------------------------------------------------------
def set_logger(logger):
    global g_logger
    g_logger = logger
#-------------------------------------------------------------------------------
# log_message
#-------------------------------------------------------------------------------
def log_message(log_level, message_format, *args):
    if(g_logger is not None):
        g_logger.log_message(log_level, message_format, *args)
    elif log_level == LOG_LEVEL_WARNING or log_level == LOG_LEVEL_ERROR:
        print(message_format.format(*args))

#-------------------------------------------------------------------------------
# log_verbose
#-------------------------------------------------------------------------------
def log_verbose(message_format, *args):
    log_message(LOG_LEVEL_VERBOSE, message_format, *args)

#-------------------------------------------------------------------------------
# log_inmessage_formation
#-------------------------------------------------------------------------------
def log_notification(message_format, *args):
    log_message(LOG_LEVEL_NOTIFICATION, message_format, *args)

#-------------------------------------------------------------------------------
def log_warning(message_format, *args):
    log_message(LOG_LEVEL_WARNING, message_format, *args)

#-------------------------------------------------------------------------------
def log_error(message_format, *args):
    log_message(LOG_LEVEL_ERROR, message_format, *args)

#-------------------------------------------------------------------------------
def start_progress(total,
                   position_formatter = None,
                   speed_formatter    = None,
                   total_formatter    = None,
                   template           = DEFAULT_BAR_TEMPLATE,
                   width              = DEFAULT_BAR_WIDTH):
    if(g_logger is not None):
        g_logger.start_progress(total               = total,
                                position_formatter  = position_formatter,
                                speed_formatter     = speed_formatter,
                                total_formatter     = total_formatter,
                                template            = template,
                                width               = width)

#-------------------------------------------------------------------------------
def update_progress(value, step_name = None):
    if(g_logger is not None):
        g_logger.update_progress(value, step_name)

#-------------------------------------------------------------------------------
def end_progress():
    if(g_logger is not None):
        g_logger.end_progress()

