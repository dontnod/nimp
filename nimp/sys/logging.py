# -*- coding: utf-8 -*-
# Copyright (c) Dontnod Entertainment

import itertools
import logging
import re


class FilteredLogging(object):
    """ Context manager to filter logging with given python filter objects as params """
    def __init__(self, *filters):
        self.context_logger = logging.getLogger()
        self.filters = filters
        self.all_nimp_loggers = (logger_name for logger_name in logging.root.manager.loggerDict)
        self.loggers_and_filters = itertools.product(self.all_nimp_loggers, self.filters)

    def __enter__(self):
        for logger_name, filter in self.loggers_and_filters:
            logging.getLogger(logger_name).addFilter(filter)
        for filter in self.filters:
            self.context_logger.addFilter(filter)
        return self.context_logger

    def __exit__(self, type, value, traceback):
        for logger_name, filter in self.loggers_and_filters:
            logging.getLogger(logger_name).removeFilter(filter)
        for filter in self.filters:
            self.context_logger.removeFilter(filter)


class SensitiveDataFilter(logging.Filter):
    """ Custom filter to hide specific information from logging stream """
    def __init__(self, *args):
        super().__init__()
        self.pattern = re.compile(rf"({'|'.join(re.escape(a) for a in args)})")

    def hide_record_args(self, args, hide_string):
        """ record args can be of various types, str, list, int """
        record_args = []
        for arg in args:
            if isinstance(arg, list):
                record_args.append([self.pattern.sub(hide_string, str(a)) for a in arg])
            elif isinstance(arg, str):
                record_args.append(self.pattern.sub(hide_string, arg))
        return tuple(record_args)

    def filter(self, record):
        hide_string = '*****'
        record.msg = self.pattern.sub(hide_string, record.msg)
        record.args = self.hide_record_args(record.args, hide_string)
        return super().filter(record)
