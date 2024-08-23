# -*- coding: utf-8 -*-
# Copyright (c) 2014-2019 Dontnod Entertainment

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

'''Git utilities'''

import logging
import giteapy
from giteapy.rest import ApiException
from datetime import datetime, timezone
import time

import nimp.sys.process


def get_branch():
    '''Get the current active branch'''
    command = 'git branch --contains HEAD'
    result, output, _ = nimp.sys.process.call(command.split(' '), capture_output=True)
    if result != 0:
        return None
    for line in output.splitlines():
        if line[0:2] == '* ':
            return line[2:].strip()
    return None


def get_version():
    '''Build a version string from the date and hash of the last commit'''
    command = 'git log -10 --date=short --pretty=format:%ct.%h'
    result, output, _ = nimp.sys.process.call(command.split(' '), capture_output=True)
    if result != 0 or '.' not in output:
        return None

    # Parse up to 10 revisions to detect date collisions
    revision_offset = 0
    for line in output.split('\n'):
        new_date, new_shorthash = line.split('.')
        utc_time = datetime.fromtimestamp(float(new_date), timezone.utc)
        new_date = utc_time.astimezone().strftime("%Y%m%d.%H%M")
        if revision_offset == 0:
            date, shorthash = new_date, new_shorthash
        elif new_date != date:
            break
        revision_offset += 1

    return '.'.join([date, str(revision_offset), shorthash])


def get_commit_version(commit_hash):
    '''Build a version string from the date and hash of a given commit'''
    command = 'git show --no-patch --date=short --pretty=format:%ct.%h ' + commit_hash
    result, output, _ = nimp.sys.process.call(command.split(' '), capture_output=True, hide_output=True)
    if result != 0 or '.' not in output:
        return None

    return output


def is_full_sha1(string):
    '''cheap logic to check if we have full git commit sha1 string'''
    if len(string) != 40:
        return False
    try:
        int(string, 16)
    except ValueError:
        return False
    return True


def gitea_has_missing_params(env):
    needed_params = ['gitea_host', 'gitea_access_token', 'gitea_repo_owner', 'gitea_repo_name']
    has_missing_params = False
    for param in needed_params:
        if not hasattr(env, param):
            has_missing_params = True
            logging.error(f"Please configure {param} parameter in project conf")
    return has_missing_params


def check_for_gitea_env(env):
    if hasattr(env, 'gitea_branches') and env.branch in env.gitea_branches:
        return True
    if hasattr(env, 'gitea_branch') and env.branch in env.gitea_branch:
        return True
    return False


def initialize_gitea_api_context(env):
    if not check_for_gitea_env(env):
        return False
    if gitea_has_missing_params(env):
        raise ValueError("You're missing mandatory gitea params in project conf")

    configuration = giteapy.Configuration()
    configuration.host = env.gitea_host
    configuration.api_key['access_token'] = env.gitea_access_token
    api_instance = giteapy.RepositoryApi(giteapy.ApiClient(configuration))
    return {'instance': api_instance, 'repo_owner': env.gitea_repo_owner, 'repo_name': env.gitea_repo_name}


def get_gitea_commit_timestamp(gitea_context, commit_sha):
    if not commit_sha:
        return None

    api_commit_timestamp = None
    try:
        api_response = gitea_context['instance'].repo_get_single_commit(
            gitea_context['repo_owner'], gitea_context['repo_name'], commit_sha
        )
        api_commit_date = api_response.commit.committer._date
        api_commit_date = datetime.fromisoformat(api_commit_date).astimezone(timezone.utc)
        api_commit_timestamp = str(round(time.mktime(api_commit_date.timetuple())))
    except ApiException as e:
        reason = str(e.reason).lower() if hasattr(e, 'reason') else ''
        logging.debug(f'[GITEA API] {gitea_context["repo_owner"]}@{gitea_context["repo_name"]}@{commit_sha} {reason}')
    return api_commit_timestamp
