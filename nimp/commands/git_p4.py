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
            type=str,
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

        parser.add_argument(
            '--changelist',
            type=str,
            default=None,
            help = 'Sync changes since this changelist'
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

        git = nimp.utils.git.Git(path, hide_output=not env.verbose)

        if not _prepare_git(env, git) and _prepare_p4(p4):
            return False

        commits = _get_git_changes(git)
        changelists = _get_p4_changes(env, p4, git)

        if changelists is None or commits is None:
            return False

        if changelists and commits:
            logging.error(
                'You have changes on both p4 and git side, refusing to sync. '
                'Reset your branch to the p4 tag and try again.'
            )
            return False
        elif changelists and not _perforce_to_git(p4, git, changelists):
            return False
        elif commits and not _git_to_perforce(p4, git, commits):
            return False
        else:
            logging.info('Nothing to sync')

        if env.push and not git('push'):
            return False

        return True

def _prepare_git(env, git):
    logging.info('Preparing git repository')
    git.set_config('core.fileMode', 'false')

    if not git('init'):
        return False

    remote = env.git_repository
    current_remote = git('remote get-url origin')
    if current_remote is None:
        if git('remote add origin {remote}', remote=remote) is None:
            return False
    else:
        current_remote = current_remote.strip()
        if current_remote != remote:
            if git('remote set-url origin {remote}', remote=remote) is None:
                return False

    branch = env.branch
    if (    git('fetch origin') is None or
            git('checkout -f {branch}', branch=branch) is None or
            git('reset --hard origin/{branch}', branch=branch) is None or
            git('branch -u origin/{branch} {branch}', branch=branch) is None):
        return False

    return True

def _prepare_p4(p4):
    logging.info('Preparing P4 workspace')
    if not p4.clean_workspace():
        return False

    return True

def _get_git_changes(git):
    commits = git('log --pretty=format:%H p4..HEAD')

    if commits is None:
        return None, None

    if commits:
        commits = commits.split('\n')

    return commits

def _get_p4_changes(env, p4, git):
    if env.changelist is None:
        p4_tag = git('tag -l p4 --format=%(subject)')
        if p4_tag is None:
            logging.error('No p4 tag is defined to mark currently synced perforce changelist.')
            return None

        values = p4_tag.strip().split(':')
        if len(values) != 2:
            logging.error('Invalid p4 tag : %s, expected cl:last_synced_cl', p4_tag.strip())
            return None
        last_synced_cl = values[1]
    else:
        last_synced_cl = env.changelist

    path_and_revision = "%s/...@%s,#head" % (git.root(), last_synced_cl)
    changelists = p4.get_changelists(path_and_revision)

    if changelists is None:
        return None

    # Skipping last C.L as it's last_synced_changelist
    return reversed(list(changelists)[:-1])

def _perforce_to_git(p4, git, changelists):
    for changelist in changelists:
        description = p4.get_changelist_description(changelist)
        description = _p4_to_utf8(description)

        _, name, email = p4.get_changelist_author(changelist)
        author = _p4_to_utf8('%s <%s>' % (name, email))

        logging.info('Syncing and commiting changelist %s', changelist)
        p4_path = git.root() + "/..."
        if not p4.sync(p4_path, cl_number=changelist):
            return False

        if git('status --porcelain'):
            if git('add .') is None:
                return False

            if git('commit . -m {message} --author {author}',
                   message=description,
                   author=author) is None:
                return False
        else:
            logging.info(' --> No changes detected, skipping')

        if not git('tag -a -f -m {message} p4 HEAD',
                   message='cl:' + changelist):
            return False

    return True

def _git_to_perforce(p4, git, commits):
    for commit in commits:
        description = git('show -s --pretty=format:%s {commit}', commit=commit)
        if description is None:
            return False

        changelist = p4.get_or_create_changelist(description)
        if changelist is None:
            return False

        files = git.root() + '/...'
        if not (p4.edit(changelist, files) and
                git('checkout', '-f', commit) and
                git('clean -fdx') and
                p4.reconcile(changelist, files)):
            return False

    return True

def _get_commits_to_sync(git):
    commits = git('log --ancestry-path --pretty=format:%H p4..HEAD')
    if commits:
        commits = commits.split('\n')
    return commits
