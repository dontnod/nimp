# -*- coding: utf-8 -*-

from datetime import datetime


#-------------------------------------------------------------------------------
DEFAULT_BAR_TEMPLATE = "{label}[{filled_chars}{empty_chars}] {position}/{total} - {time_left} - {step_name}"
DEFAULT_BAR_WIDTH    = 15

#-------------------------------------------------------------------------------
LOG_LEVEL_VERBOSE      = 1
LOG_LEVEL_NOTIFICATION = 2
LOG_LEVEL_WARNING      = 3
LOG_LEVEL_ERROR        = 4

#-------------------------------------------------------------------------------
g_logger = None

#-------------------------------------------------------------------------------
def set_logger(logger):
    global g_logger
    g_logger = logger


#-------------------------------------------------------------------------------
def log_prefix():
    ts = datetime.utcnow().strftime('%H:%M:%S.%f')[:-3]
    return "[%s] Nimp: " % (ts)

#-------------------------------------------------------------------------------
def log_message(log_level, prefix, message_format, *args):
    if prefix:
        message_format = log_prefix() + message_format
    if(g_logger is not None):
        g_logger.log_message(log_level, message_format, *args)
    elif log_level == LOG_LEVEL_WARNING or log_level == LOG_LEVEL_ERROR:
        print(message_format.format(*args))

#-------------------------------------------------------------------------------
def log_verbose(message_format, *args, **kwargs):
    log_message(LOG_LEVEL_VERBOSE, True, message_format, *args)

#-------------------------------------------------------------------------------
def log_notification(message_format, *args):
    log_message(LOG_LEVEL_NOTIFICATION, True, message_format, *args)

#-------------------------------------------------------------------------------
def log_warning(message_format, *args):
    log_message(LOG_LEVEL_WARNING, True, message_format, *args)

#-------------------------------------------------------------------------------
def log_error(message_format, *args):
    log_message(LOG_LEVEL_ERROR, True, message_format, *args)

#-------------------------------------------------------------------------------
def start_progress(total,
                   position_formatter  = None,
                   speed_formatter     = None,
                   total_formatter     = None,
                   step_name_formatter = None,
                   template            = DEFAULT_BAR_TEMPLATE,
                   width               = DEFAULT_BAR_WIDTH):
    if(g_logger is not None):
        g_logger.start_progress(total               = total,
                                position_formatter  = position_formatter,
                                speed_formatter     = speed_formatter,
                                total_formatter     = total_formatter,
                                step_name_formatter = step_name_formatter,
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

#-------------------------------------------------------------------------------
def log_progress(items,
                 position_formatter  = None,
                 speed_formatter     = None,
                 total_formatter     = None,
                 step_name_formatter = None):
    start_progress(len(items),
                   position_formatter  = position_formatter,
                   speed_formatter     = speed_formatter,
                   total_formatter     = total_formatter,
                   step_name_formatter = step_name_formatter)
    i = 0
    for item in items:
        i = i + 1
        update_progress(i, item)
        yield item
    end_progress()
