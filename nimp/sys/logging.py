# -*- coding: utf-8 -*-
# Copyright (c) Dontnod Entertainment

import logging
import re


class FilteredLogging(object):
    """ Context manager to filter logging with given python filter objects as params """
    def __init__(self, *filters):
        self.logger = logging.getLogger()
        self.filters = filters

    def __enter__(self):
        for filter in self.filters:
            self.logger.addFilter(filter)
        return self.logger

    def __exit__(self, type, value, traceback):
        for filter in self.filters:
            self.logger.removeFilter(filter)


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
            else:
                record_args.append(self.pattern.sub(hide_string, str(arg)))
        return tuple(record_args)

    def filter(self, record):
        hide_string = '*****'
        record.msg = self.pattern.sub(hide_string, record.msg)
        record.args = self.hide_record_args(record.args, hide_string)
        return super().filter(record)
