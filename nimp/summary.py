# -*- coding: utf-8 -*-
# Copyright © 2014—2016 Dontnod Entertainment

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
''' Class and function relative to the nimp environment, i.e. configuration
values and command line parameters set for this nimp execution '''

import collections
import logging
import re
import sys

class SummaryHandler(logging.Handler):
    """ Base class for summary handler.
        Summary handlers are responsible for parsing output log and outputing
        a comprehensive summary of what went wrong """
    def __init__(self, env):
        super().__init__(logging.DEBUG)
        self._env = env
        self._ignore_patterns = []
        self._error_patterns = []
        self._warning_patterns = []
        self._context_patterns = []
        self._has_errors = False
        self._has_warnings = False

        error_patterns = [
            #GCC
            r'[\/\w\W\-. ]+:\d+:\d+: (fatal )?error: .*', #GCC errors
            r'[\/\w\W\-. ]+:\d+: undefined reference to .*', #GCC linker error

            # Clang
            r'[\/\w\W\-. ]+\(\d+,\d+\): (fatal ?)error : .*',
            r'[\/\w\W\-. ]+ : error : [A-Z0-9]+: reference to undefined symbol.*',
            r'^duplicate symbol \w+ in:',
            r': multiple definition of ',
            r'clang: error: no such file or directory:.*',

            #.NET / Mono
            r'[\/\w\W\-. ]+\(\d+,\d+\) : error [A-Z\d]+: .*',

            #MSVC
            r'[\/\w\W\-. ]+\(\d+\): error [A-Z\d]+: .*',
            r'[\/\w\W\-. ]+\ : error [A-Z\d]+: unresolved external symbol .*',
        ]

        warning_patterns = [
            r'[\/\w\W\-.: ]+\(\d+,\d+\) : warning [A-Z\d]+: .*', # MSVC .NET / Mono
            r'[\/\w\W\-.: ]+:\d+:\d+: warning: .*', # GCC
            r'[\/\w\W\-.: ]+\(\d+,\d+\): warning : .*', # Clang
            r'[\/\w\W\-.: ]+\(\d+\): warning [A-Z\d]+: .*' # MSVC
        ]

        ignore_patterns = [
        ]

        self._compile_patterns(ignore_patterns,
                               'ignore_patterns',
                               self._ignore_patterns)

        self._compile_patterns(error_patterns,
                               'error_patterns',
                               self._error_patterns)

        self._compile_patterns(warning_patterns,
                               'warning_patterns',
                               self._warning_patterns)

        self._compile_patterns([],
                               'context_patterns',
                               self._context_patterns)

    def _compile_patterns(self, patterns, key, destination):
        config_key = 'summary_%s' % key
        if hasattr(self._env, config_key):
            additionnal_patterns = getattr(self._env, config_key)
            if additionnal_patterns is not None:
                patterns.extend(additionnal_patterns)

        for pattern in patterns:
            try:
                destination.append(re.compile(pattern))
            #pylint: disable=broad-except
            except Exception as ex:
                logging.error('Error while compiling pattern %s: %s',
                              pattern, ex)

    def __enter__(self):
        # Sets up logging
        log_level = logging.INFO
        if getattr(self._env, 'verbose'):
            log_level = logging.DEBUG

        root_logger = logging.root

        # Need to do that because some log may already have been output
        for handler in list(logging.root.handlers):
            root_logger.removeHandler(handler)

        logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s',
                            level=log_level)

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

        return self

    def __exit__(self, ex_type, value, traceback):
        if self._env.summary is not None:
            summary = self._env.summary
            # So we can print summary to stdout
            if summary.lower() == 'stdout':
                self._write_summary(sys.stdout)
            else:
                with open(summary, 'w') as out:
                    self._write_summary(out)

    def has_errors(self):
        ''' Returns true if errors were emmited durring program execution '''
        return self._has_errors

    def has_warnings(self):
        ''' Returns true if warnings were emmited durring program execution '''
        return self._has_warnings

    def emit(self, record):
        msg = record.getMessage()

        for pattern in self._ignore_patterns:
            if pattern.match(msg):
                self._add_notif(msg)
                return

        if record.levelno == logging.CRITICAL or record.levelno == logging.ERROR:
            self._add_error(record.getMessage())
            self._has_errors = True
            return
        if record.levelno == logging.WARNING:
            self._add_warning(record.getMessage())
            self._has_warnings = True
            return

        if SummaryHandler._match_message(self._error_patterns,
                                         msg,
                                         self._add_error):
            self._has_errors = True

        elif self._match_message(self._warning_patterns,
                                 msg,
                                 self._add_warning):
            self._has_warnings = True

        else:
            self._add_notif(msg)

    @staticmethod
    def _match_message(patterns, msg, add_callback):
        for pattern in patterns:
            match = pattern.match(msg)
            if match is not None:
                group_dict = match.groupdict()
                if 'message' in group_dict:
                    msg = group_dict['message']

                add_callback(msg)
                return True
        return False

    def _add_notif(self, msg):
        pass

    def _add_warning(self, msg):
        pass

    def _add_error(self, msg):
        pass

    def _write_summary(self, destination):
        pass


class DefaultSummaryHandler(SummaryHandler):
    """ Default summary handler, showing one line by error / warning and
    adding three lines of context before / after errors """
    def __init__(self, env):
        super().__init__(env)
        self._summary = ''
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
        show_context = len(self._context) < self._context.maxlen
        show_context = show_context and (self._has_errors or self._has_warnings)
        if show_context:
            self._summary += '[  NOTIF  ] %s\n' % (msg,)

    def _add_warning(self, msg):
        if len(self._context) == self._context.maxlen:
            self._summary += '\n *********************************************\n'
            while len(self._context) > 0:
                self._summary += '[  NOTIF  ] %s\n' % (self._context.popleft(),)
        self._summary += '[ WARNING ] %s\n' % (msg,)

    def _add_error(self, msg):
        if len(self._context) == self._context.maxlen:
            self._summary += '\n *********************************************\n'
            while len(self._context) > 0:
                self._summary += '[  NOTIF  ] %s\n' % (self._context.popleft(),)
        self._summary += '[  ERROR  ] %s\n' % (msg,)

    def _write_summary(self, destination):
        ''' Writes summary to destination '''
        destination.write(self._summary)
