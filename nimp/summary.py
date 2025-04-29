# -*- coding: utf-8 -*-
# Copyright © 2014–2025 Dontnod Entertainment

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

'''Class and function relative to the nimp environment, i.e. configuration
values and command line parameters set for this nimp execution'''

import collections
import logging
from logging.handlers import WatchedFileHandler
import os
import re
import sys


class SummaryHandler(logging.Handler):
    """Base class for summary handler.
    Summary handlers are responsible for parsing output log and outputing
    a comprehensive summary of what went wrong"""

    def __init__(self, env):
        super().__init__(logging.DEBUG)

        if "NIMP_LOG_FILE" in os.environ:
            self.log_all_handler = WatchedFileHandler(os.environ["NIMP_LOG_FILE"])
            self.log_all_handler.setLevel(logging.DEBUG)
            self.log_all_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

        self._env = env
        self._ignore_patterns = []
        self._error_patterns = []
        self._warning_patterns = []
        self._context_patterns = []
        self._summary = {'errors': [], 'warnings': []}

        error_patterns = [
            # GCC
            r'[\/\w\W\-. ]+:\d+:\d+: (fatal )?error: .*',  # GCC errors
            r'[\/\w\W\-. ]+:\d+: undefined reference to .*',  # GCC linker error
            # Clang
            r'[\/\w\W\-. ]+\(\d+,\d+\): (fatal ?)error : .*',
            r'[\/\w\W\-. ]+ : error : [A-Z0-9]+: reference to undefined symbol.*',
            r'^duplicate symbol \w+ in:',
            r': multiple definition of ',
            r'clang: error: no such file or directory:.*',
            # .NET / Mono
            r'[\/\w\W\-. ]+\(\d+,\d+\) : error [A-Z\d]+: .*',
            # MSVC
            r'[\/\w\W\-. ]+\(\d+\): error [A-Z\d]+: .*',
            r'[\/\w\W\-. ]+\ : error [A-Z\d]+: unresolved external symbol .*',
            # PS4 SDK (Orbis)
            r'\[Error\]\t.*',
            # XboxOne SDK
            r' - Error Code: .*',
            r'Package was not created, error = .*',
            r'Chunk [0-9]+ is invalid: it contains 0 files\.',
            r'The layout contained an invalid chunk\.',
            r'Chunks must contain at least 1 non-empty file\.',
            r'FileGroup .* did not match any files\.',
        ]

        warning_patterns = [
            r'[\/\w\W\-.: ]+\(\d+,\d+\) : warning [A-Z\d]+: .*',  # MSVC .NET / Mono
            r'[\/\w\W\-.: ]+:\d+:\d+: warning: .*',  # GCC
            r'[\/\w\W\-.: ]+\(\d+,\d+\): warning : .*',  # Clang
            r'[\/\w\W\-.: ]+\(\d+\): warning [A-Z\d]+: .*',  # MSVC
            r'\[Warn\]\t.*',  # PS4 SDK (Orbis)
        ]

        ignore_patterns = [
            r'  WARNING - appdata.bin is being created automatically for this package',
        ]

        self._compile_patterns(ignore_patterns, 'ignore_patterns', self._ignore_patterns)

        self._compile_patterns(error_patterns, 'error_patterns', self._error_patterns)

        self._compile_patterns(warning_patterns, 'warning_patterns', self._warning_patterns)

        self._compile_patterns([], 'context_patterns', self._context_patterns)

    def _compile_patterns(self, patterns, key, destination):
        config_key = 'summary_%s' % key
        if hasattr(self._env, config_key):
            additionnal_patterns = getattr(self._env, config_key)
            if additionnal_patterns is not None:
                patterns.extend(additionnal_patterns)

        for pattern in patterns:
            try:
                destination.append(re.compile(pattern))
            # pylint: disable=broad-except
            except Exception as ex:
                logging.error('Error while compiling pattern %s: %s', pattern, ex)

    def __enter__(self):
        # Sets up logging
        log_level = logging.INFO
        if getattr(self._env, 'verbose'):
            log_level = logging.DEBUG

        root_logger = logging.root

        # If stdout is not a TTY, fall back to the old log format. This is just in case there
        # are external tools that parse the output, we don’t want to break them.
        if not sys.stdout.isatty():
            for handler in list(logging.root.handlers):
                root_logger.removeHandler(handler)
            logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=log_level)

        child_processes_logger = logging.getLogger('child_processes')
        child_processes_logger.propagate = False
        child_processes_logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(message)s'))
        child_processes_logger.addHandler(handler)

        # Enables warnings and errors recording
        if self._env.summary is not None:
            root_logger.addHandler(self)
            child_processes_logger.addHandler(self)
            if hasattr(self, "log_all_handler"):
                child_processes_logger.addHandler(self.log_all_handler)

        return self

    def __exit__(self, ex_type, value, traceback):
        if self._env.summary is not None:
            summary = self._env.summary
            # So we can print summary to stdout
            if summary.lower() == 'stdout':
                self._write_summary(sys.stdout)
            else:
                with open(summary, 'w', encoding='utf-8') as out:
                    self._write_summary(out)

    def has_errors(self):
        '''Returns true if errors were emitted during program execution'''
        return len(self._summary['errors']) > 0

    def has_warnings(self):
        '''Returns true if warnings were emitted during program execution'''
        return len(self._summary['warnings']) > 0

    def emit(self, record):
        msg = record.getMessage()

        for pattern in self._ignore_patterns:
            if pattern.match(msg):
                self._add_notif(msg)
                return

        if record.levelno == logging.CRITICAL or record.levelno == logging.ERROR:
            self._add_msg('error', self.format(record))
            return
        if record.levelno == logging.WARNING:
            self._add_msg('warning', self.format(record))
            return
        else:
            self._add_notif(msg)
        self._match_message(self._error_patterns, msg, 'error')
        self._match_message(self._warning_patterns, msg, 'warning')

    def _match_message(self, patterns, msg, notif_lvl):
        for pattern in patterns:
            match = pattern.match(msg)
            if match is not None:
                group_dict = match.groupdict()
                if 'message' in group_dict:
                    msg = group_dict['message']
                self._add_msg(notif_lvl, msg)
                return True
        return False

    def _add_notif(self, msg):
        pass

    def _add_msg(self, notif_lvl, msg):
        pass

    def _write_summary(self, destination):
        pass


class DefaultSummaryHandler(SummaryHandler):
    """Default summary handler, showing one line by error / warning and
    adding three lines of context before / after errors"""

    def __init__(self, env):
        super().__init__(env)
        self._context = collections.deque([], 4)

    def _add_notif(self, msg):
        for pattern in self._context_patterns:
            match = pattern.match(msg)
            if match is not None:
                group_dict = match.groupdict()
                if 'message' in group_dict:
                    msg = group_dict['message']
                    break
        self._context.append(msg)

    def _add_msg(self, notif_lvl, msg):
        self._summary[f'{notif_lvl}s'].append('\n *********************************************\n')
        if len(self._context) == self._context.maxlen:
            while self._context:
                self._summary[f'{notif_lvl}s'].append('[  NOTIF  ] %s\n' % (self._context.popleft(),))
        self._summary[f'{notif_lvl}s'].append(f'[ {notif_lvl.upper()} ] {msg}\n')

    def _write_summary(self, destination):
        '''Writes summary to destination'''
        for lvl in ['errors', 'warnings']:
            destination.writelines(self._summary[lvl])
