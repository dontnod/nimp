# -*- coding: utf-8 -*-

import time
import argparse

import nimp.modules.loggers
import nimp.modules.log_formats

from nimp.modules.loggers.logger        import *
from nimp.modules.log_formats.format    import *
from nimp.modules.module                import *

from nimp.utilities.inspection          import *
from nimp.utilities.files               import *
from nimp.utilities.logging             import *

#-------------------------------------------------------------------------------
class LoggingModule(Module):
    #---------------------------------------------------------------------------
    def __init__(self):
        Module.__init__(self, "logging", ["configuration"])
        self._formats = {}
        self._loggers = {}
        formats_instances = get_instances(nimp.modules.log_formats, Format)
        loggers_instances = get_instances(nimp.modules.loggers, Logger)

        for format_instance_it in formats_instances:
            self._formats[format_instance_it.name()] = format_instance_it

        for logger_instance_it in loggers_instances:
            self._loggers[logger_instance_it.name()] = logger_instance_it

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        log_group = parser.add_argument_group("Logging")

        log_group.add_argument('--log-format',
                               help='Set log format',
                               metavar = "FORMAT_NAME",
                               type=str,
                               default="standard",
                               choices   = self._formats)

        log_group.add_argument('--logger',
                               help='Set logger',
                               metavar = "LOGGER_NAME",
                               type=str,
                               default="console",
                               choices   = self._loggers)

        log_group.add_argument('-v',
                               '--verbose',
                               help='Enable verbose mode',
                               default=False,
                               action="store_true")
        return True

    #---------------------------------------------------------------------------
    def load(self, context):
        global g_logger

        logger_name     = context.logger
        format_name     = context.log_format

        logger          = self._loggers[logger_name]
        format          = self._formats[format_name]

        logger.initialize(format, context, context.verbose)

        set_logger(logger)

        log_verbose("Logger initialized")
        return True
