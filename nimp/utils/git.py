# -*- coding: utf-8 -*-
# Copyright © 2014—2019 Dontnod Entertainment

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

''' Git utilities '''

import nimp.sys.process

class GitError(Exception):
    ''' Raised when a git command returns an error '''
    def __init__(self, value):
        super().__init__(self, value)
        self.value = value
    def __str__(self):
        return repr(self.value)

def get_branch():
    ''' Get the current active branch '''
    command = 'git branch --contains HEAD'
    result, output, _ = nimp.sys.process.call(command.split(' '), capture_output=True)
    if result != 0:
        return None
    for line in output.splitlines():
        if line[0:2] == '* ':
            return line[2:].strip()
    return None

def get_version():
    ''' Build a version string from the date and hash of the last commit '''
    from datetime import datetime, timezone
    command = 'git log -10 --date=short --pretty=format:%ct.%h'
    result, output, _ = nimp.sys.process.call(command.split(' '), capture_output=True)
    if result != 0 or '.' not in output:
        return None
    # Parse up to 10 revisions to detect date collisions
    line_id = 0
    for line in output.split('\n'):
        new_date, new_shorthash = line.split('.')
        utc_time = datetime.fromtimestamp(float(new_date), timezone.utc)
        new_date = utc_time.astimezone().strftime("%Y%m%d.%H%M")
        if line_id == 0:
            date, shorthash = new_date, new_shorthash
        elif new_date != date:
            break
        line_id += 1
    return '.'.join([date, str(line_id), shorthash])

class Git():
    ''' Wrapper representing a given git repository cloned in a given
        directory '''

    def __init__(self, directory, hide_output=False):
        self._directory = directory
        self._hide_output = hide_output
        self._config = {}

    def root(self):
        ''' Returns the root directory of the git repository '''
        return self._directory

    def set_config(self, option, value):
        ''' Sets the given option for further calls to this Git instance '''
        self._config[option] = value

    def __call__(self, git_command, **kwargs):
        command = ['git']
        for option, value in self._config.items():
            command += ['-c', '%s=%s' % (option, value)]
        command += [it.format(**kwargs) for it in git_command.split(' ')]

        result, output, error = nimp.sys.process.call(
            command,
            capture_output=True,
            hide_output=self._hide_output,
            cwd=self._directory
        )

        if result != 0:
            raise GitError(error)

        return output

    def check(self, command, **kwargs):
        ''' Returns true if the command succeed, false otherwise '''
        try:
            self(command, **kwargs)
        except GitError:
            return False

        return True
