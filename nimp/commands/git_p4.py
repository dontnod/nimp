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

''' Import Perforce Changes in a git repository. '''

import logging
import shutil
import ast

import nimp.command
import nimp.commands.p4
import nimp.utils.git
import nimp.utils.p4

def _is_git_available():
    if shutil.which('git') is None:
        return False, ('git executable was not found on your system, check your'
                       'installation.')
    return True, ''

def _p4_to_utf8(value):
    value = value.replace('"', '\\"')
    value = '"%s"' % value
    return ast.literal_eval(value)

class GitP4(nimp.command.Command):
    ''' Imports P4 changelist in a git branch '''

    def configure_arguments(self, env, parser):
        nimp.utils.p4.add_arguments(parser)
        parser.add_argument(
            'p4_path',
            metavar = '<path>',
            help = 'Root of remote p4 directory to synchronize with git'
        )

        parser.add_argument(
            'git_repository',
            metavar = '<url>',
            help = 'Url of git repository to sync'
        )

        parser.add_argument(
            'branch',
            metavar = '<git-branch>',
            help = 'Branch to sync with perforce'
        )

        parser.add_argument(
            '--push',
            action='store_true',
            help = 'Push result to git'
        )
        return True

    def is_available(self, env):
        return _is_git_available() and nimp.commands.p4.is_p4_available()

    def run(self, env):
        p4 = nimp.utils.p4.P4(hide_output=not env.verbose)
        path = p4.get_local_path(env.p4_path)

        if path is None:
            logging.error(
                ('Unable to map remote perforce path %s to local path, '
                 'check that this path is mapped in your P4 client view.'),
                env.p4_path
            )
            return False

        logging.info('Cleaning P4 workspace')
        if not p4.clean_workspace():
            return False

        logging.info('Setting up git repository')
        git = nimp.utils.git.Git(
            path,
            hide_output = not env.verbose)
        git.set_config('core.fileMode', 'false')

        if not git.reset(env.git_repository, env.branch):
            return False

        p4_tag = git.get_tag('p4', 'subject')
        if p4_tag is None:
            logging.error('No p4 tag is defined to mark currently synced perforce changelist.')
            return False

        last_synced_changelist = p4_tag['subject'].split(':')[1]
        changelists = p4.get_changelists(
            "%s/...@%s,#head" % (path, last_synced_changelist)
        )

        # Skipping last C.L as it's last_synced_changelist
        changelists = reversed(list(changelists)[:-1])

        for changelist in changelists:
            description = p4.get_changelist_description(changelist)
            description = _p4_to_utf8(description)

            _, name, email = p4.get_changelist_author(changelist)
            author = _p4_to_utf8('%s <%s>' % (name, email))

            p4_path = path + "/..."
            logging.info('Syncing and commiting changelist %s', changelist)
            if not p4.sync(p4_path, cl_number=changelist):
                return False

            if git.have_changes():
                if not git.commit_all(description, author=author):
                    return False
            else:
                logging.info(' --> No changes detected, skipping')

            if not git.force_set_tag('p4', env.branch, 'cl:%s' % changelist):
                return False

        if env.push and not git.push():
            return False

        return True
