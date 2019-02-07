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

import ast
import os
import nimp.sys.process

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

    def __init__(self, directory, url):
        self._directory = directory
        self._url = url

    def reset(self, branch='master'):
        ''' Sets correct origin and checkouts / resets the given branch
            to the state of the origin branch. This may overwrite origin
            remote url to the value given in the constructor.'''

        if not os.path.isdir(os.path.join(self._directory, '.git')):
            if self._git('init')[0] != 0:
                return False
        elif self._git('status')[0] != 0:
            if not self._git('init'):
                return False

        if self._git('remote', 'show', 'origin')[0] != 0:
            if self._git('remote', 'add', 'origin', self._url)[0] != 0:
                return False
        elif self._git('remote', 'set-url', 'origin', self._url)[0] != 0:
            return False

        if self._git('fetch', 'origin')[0] != 0:
            return False

        if self._git('checkout', '-f', branch)[0] != 0:
            return False

        if self._git('reset', '--hard', 'origin/%s' % branch)[0] != 0:
            return False

        return True

    def have_changes(self):
        ''' Returns true if there is local changes in the repository '''
        return self._git('diff', '--exit-code')[0] != 0

    def commit_all(self, commit_message, author=None):
        ''' Commmits all untracked changes with the given commit message
            and given author '''
        command = ['commit', '.', '-m', commit_message]
        if author is not None:
            command += ['--author', author]

        if self._git(*command)[0] != 0:
            return False

        return True

    def force_set_tag(self, tag, commit, message):
        ''' Sets the given tag to point on the given commit with the given
            message, overwrites the tag if it exists '''
        if self._git('tag', '-a', '-f', '-m', message, tag, commit)[0] != 0:
            return False
        return True

    def get_tag(self, tag_name, *fields):
        ''' Returns a dictionnary containing requested fields of given tag.
            The fields are those allowed in the --format option of git tag '''
        format_str = '{'
        for field in fields:
            format_str += "'{0}': '%({0})',".format(field)
        format_str += '}'

        result, output, _ = self._git(
            'tag', '-l', tag_name,
            '--format=%s' % format_str
        )

        if result != 0:
            return None

        return ast.literal_eval(output)

    def _git(self, *args):
        return nimp.sys.process.call(
            ['git'] + list(args),
            capture_output=True,
            cwd=self._directory
        )
