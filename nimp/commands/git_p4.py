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

import ast
import logging
import shutil

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
            metavar = '<branch>',
            help = 'Branch to sync with perforce'
        )

        parser.add_argument(
            '--push',
            action='store_true',
            help = 'Push result to git'
        )

        parser.add_argument(
            '--merge',
            metavar = '<branch>',
            help = 'Try to merge this branch after updating P4 and submit the result to P4',
            default=None
        )

        parser.add_argument(
            '--changelist',
            type=str,
            default=None,
            help = 'Sync changes since this changelist (excluded)'
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

        try:
            return _sync(env, p4, git)
        except nimp.utils.git.GitError as error:
            logging.error('Error while running git command : %s', error)
            return False

def _sync(env, p4, git):
    _prepare_git(env, git)

    last_synced_cl = _get_last_synced_cl(env, git)
    if last_synced_cl is None:
        return False

    if not _prepare_p4(p4, git, last_synced_cl):
        return False

    commits = _get_git_changes(git)
    changelists = _get_p4_changes(p4, git, last_synced_cl)

    if changelists is None:
        return False

    if not changelists and not commits and env.merge is None:
        logging.info('Nothing to sync')
        return True

    if changelists and commits:
        logging.error(
            'You have changes on both p4 and git side, refusing to sync. '
            'Reset your branch to the p4 tag and try again.'
        )
        return False

    if changelists and not _perforce_to_git(p4, git, changelists):
        return False

    if env.merge is not None:
        git('merge --no-ff --log=50 {branch}', branch=env.merge)

        # Cleaning so that we recover a clean P4 state in order to
        # checkout files for synchronization
        if not p4.clean(git.root() + '/...'):
            return False

        commits = _get_git_changes(git)

    if commits and not _git_to_perforce(p4, git, commits):
        return False

    if env.push:
        git('push -f --tags origin {branch}', branch=env.branch)

    return True

def _prepare_git(env, git):
    logging.info('Preparing git repository')
    git.set_config('core.fileMode', 'false')

    git('init')

    remote = env.git_repository
    if not git.check('remote get-url origin'):
        git('remote add origin {remote}', remote=remote)
    else:
        current_remote = git('remote get-url origin').strip()
        if current_remote != remote:
            git('remote set-url origin {remote}', remote=remote)

    branch = env.branch
    git('submodule init')
    git('fetch --tags origin')

    if not git.check('rev-parse --verify {branch}', branch=branch):
        git('branch {branch} origin/{branch}', branch=branch)

    git('symbolic-ref HEAD refs/heads/{branch}', branch=branch)
    git('reset --quiet --mixed origin/{branch}', branch=branch)

def _get_last_synced_cl(env, git):
    if env.changelist is None:
        if not git.check('tag -l p4 --format=%(subject)') :
            logging.error('No p4 tag is defined to mark currently synced'
                          'perforce changelist. Try to use --changelist'
                          'parameter')
            return False
        p4_tag = git('tag -l p4 --format=%(subject)')
        values = p4_tag.strip().split(':')

        if len(values) != 2:
            logging.error('Invalid p4 tag : %s, expected cl:last_synced_cl',
                          p4_tag.strip())
            return False
        return values[1]

    return env.changelist

def _prepare_p4(p4, git, last_synced_cl):
    logging.info('Preparing P4 workspace')
    if not p4.clean_workspace():
        return False

    root = git.root() + '/...'
    if not p4.clean(root):
        return False

    if not p4.sync(root, cl_number=last_synced_cl):
        return False

    return True

def _get_git_changes(git):
    commits = git('log --ancestry-path --pretty=format:%H p4..HEAD')

    if commits:
        commits = commits.split('\n')

    return commits

def _get_p4_changes(p4, git, last_synced_cl):
    path_and_revision = "%s/...@%s,#head" % (git.root(), last_synced_cl)
    changelists = p4.get_changelists(path_and_revision)

    if changelists is None:
        return None

    # Skipping last C.L as it's last_synced_changelist
    return list(reversed(list(changelists)[:-1]))

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

        if git.check('status --porcelain'):
            git('add .')
            git('commit . -m {message} --author {author}',
                message=description,
                author=author)
        else:
            logging.info(' --> No changes detected, skipping')

        message = 'cl:%s' % changelist
        git('tag -a -f -m {message} p4 HEAD', message=message)

    return True

def _git_to_perforce(p4, git, commits):
    files = git.root() + '/...'

    if not p4.sync(files):
        return False

    for commit in commits:
        logging.info('Submiting commit %s', commit)
        description = git('show -s --pretty=format:%B {commit}', commit=commit)
        changelist = p4.get_or_create_changelist(description)
        if changelist is None:
            return False

        if not p4.edit(changelist, files):
            return False

        git('checkout -q -f {commit}', commit=commit)
        git('submodule update --init --recursive')
        git('clean -fdx')

        if not p4.reconcile(changelist, files):
            return False

        if not p4.submit(changelist):
            return False

    return True

def _get_commits_to_sync(git):
    commits = git('log --ancestry-path --pretty=format:%H p4..HEAD')
    if commits:
        commits = commits.split('\n')
    return commits
