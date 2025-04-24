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

from __future__ import annotations

import logging
import os
import subprocess
import time
from datetime import datetime
from datetime import timezone
from pathlib import Path
from typing import TypedDict

import giteapy
from giteapy.rest import ApiException

import nimp.sys.process


class GitApiContext(TypedDict):
    instance: giteapy.RepositoryApi
    repo_owner: str
    repo_name: str


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


def maybe_git_revision(candidate: str) -> bool:
    return candidate.isalnum() and candidate.islower()


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


def check_for_gitea_env(env) -> bool:
    if hasattr(env, 'gitea_branches') and env.branch in env.gitea_branches:
        return True
    if hasattr(env, 'gitea_branch') and env.branch in env.gitea_branch:
        return True
    return False


def initialize_gitea_api_context(env) -> GitApiContext | None:
    if not check_for_gitea_env(env):
        return None
    if gitea_has_missing_params(env):
        raise ValueError("You're missing mandatory gitea params in project conf")

    configuration = giteapy.Configuration()
    configuration.host = env.gitea_host
    configuration.api_key['access_token'] = env.gitea_access_token
    api_instance = giteapy.RepositoryApi(giteapy.ApiClient(configuration))
    return {'instance': api_instance, 'repo_owner': env.gitea_repo_owner, 'repo_name': env.gitea_repo_name}


def get_gitea_commit_timestamp(gitea_context: GitApiContext, commit_sha: str | None) -> str | None:
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


def get_git_dir(cwd: os.PathLike[str] | str | None = None) -> str | None:
    process = subprocess.run(
        ["git", "rev-parse", "--git-dir"],
        text=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
    )
    if process.returncode == 0:
        return process.stdout.strip()

    return None


def is_shallow_repository(cwd: os.PathLike[str] | str | None = None) -> bool | None:
    process = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        text=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
    )
    if process.returncode == 0:
        return {"true": True, "false": False}.get(process.stdout.strip().lower())

    return None


def add_alternates(*alternates: str, cwd: os.PathLike[str] | str | None = None) -> None:
    git_dir = get_git_dir(cwd)
    if git_dir is None:
        return

    if not Path(git_dir).is_dir():
        # git-dir might be a file pointing to the real git-dir
        # Ignore this case for now
        return

    alternates_file = Path(git_dir, "objects/info/alternates")
    alternates_file.parent.mkdir(parents=True, exist_ok=True)

    current_alternates = []
    if alternates_file.is_file():
        current_alternates = alternates_file.read_text().splitlines(keepends=False)

    new_alternates = set(alternates).difference(current_alternates)

    current_alternates.extend(new_alternates)

    alternates_file.write_text('\n'.join(current_alternates))


def get_remotes(cwd: os.PathLike[str] | str) -> list[str]:
    return subprocess.run(
        ['git', 'remote'],
        text=True,
        cwd=cwd,
        stdout=subprocess.PIPE,
    ).stdout.splitlines(keepends=False)


def rev_parse_verify(revision: str, cwd: os.PathLike[str] | str | None = None) -> str | None:
    process = subprocess.run(
        ['git', 'rev-parse', '--verify', revision],
        check=False,
        capture_output=False,
        stdout=subprocess.PIPE,
        text=True,
        cwd=cwd,
    )
    if process.returncode == 0:
        return process.stdout.strip()
    return None
