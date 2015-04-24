# -*- coding: utf-8 -*-

import time
import argparse

import nimp.modules.log_formats

from nimp.modules.logger                import *
from nimp.modules.log_formats.format    import *
from nimp.modules.module                import *
from nimp.utilities.inspection          import *
from nimp.utilities.logging             import *

#-------------------------------------------------------------------------------
class LoggingModule(Module):
    #---------------------------------------------------------------------------
    def __init__(self):
        Module.__init__(self, "logging", ["configuration"])
        self._formats = {}
        formats_instances = get_instances(nimp.modules.log_formats, Format)

        for format_instance_it in formats_instances:
            self._formats[format_instance_it.name()] = format_instance_it

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        log_group = parser.add_argument_group("Logging")

        log_group.add_argument('--log-format',
                               help='Set log format',
                               metavar = "FORMAT_NAME",
                               type=str,
                               default="standard",
                               choices   = self._formats)


        log_group.add_argument('-v',
                               '--verbose',
                               help='Enable verbose mode',
                               default=False,
                               action="store_true")
        return True

    #---------------------------------------------------------------------------
    def load(self, env):
        global g_logger
        format_name     = env.log_format
        format          = self._formats[format_name]
        logger          = Logger(format, env.verbose)
        set_logger(logger)
        return True
