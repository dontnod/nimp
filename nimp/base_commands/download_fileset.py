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

'''Downloads a previously uploaded fileset to the local workspace'''

from __future__ import annotations

import copy
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Iterator

import nimp.artifacts
import nimp.command
import nimp.system
from nimp.environment import Environment
from nimp.utils import git

if TYPE_CHECKING:
    from giteapy.models.repository import Repository


class DownloadFileset(nimp.command.Command):
    '''Downloads a previously uploaded fileset to the local workspace'''

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'dry_run', 'free_parameters')
        parser.add_argument('--revision', metavar='<revision>', help='find a revision equal to this one')
        parser.add_argument('--max-revision', metavar='<revision>', help='find a revision older or equal to this one')
        parser.add_argument('--min-revision', metavar='<revision>', help='find a revision newer or equal to this one')
        parser.add_argument('--destination', metavar='<path>', help='set a destination relative to the workspace')
        parser.add_argument(
            '--track',
            choices=['binaries', 'symbols', 'package', 'staged'],
            help='track the installed revision in the workspace status',
        )
        parser.add_argument(
            '--prefer-http',
            action='store_true',
            help='If "artifact_http_repository_source" is provided in env, the download will be done through HTTP request intead of file copy',
        )

        parser.add_argument('fileset', metavar='<fileset>', help='fileset to download')
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env: Environment) -> bool:
        api_context = git.initialize_gitea_api_context(env)

        artifacts_source: str = env.artifact_repository_source
        if env.prefer_http:
            artifacts_http_source = getattr(env, 'artifact_http_repository_source', None)
            if artifacts_http_source:
                artifacts_source = artifacts_http_source
            else:
                logging.warning('prefer-http provided but no artifact_http_repository_source in configuration')

        artifact_uri_pattern: str = artifacts_source.rstrip('/') + '/' + str(env.artifact_collection[env.fileset])

        install_directory = env.root_dir
        if env.destination:
            install_directory = str(PurePosixPath(install_directory) / env.format(env.destination))

        format_arguments = copy.deepcopy(vars(env))
        logging.info('Searching %s', artifact_uri_pattern.format_map({**format_arguments, 'revision': '*'}))
        all_artifacts = nimp.system.try_execute(
            lambda: nimp.artifacts.list_artifacts(artifact_uri_pattern, format_arguments, api_context),
            OSError,
        )
        artifact_to_download = DownloadFileset._find_matching_artifact(
            all_artifacts,
            env.revision,
            env.min_revision,
            env.max_revision,
            api_context,
        )

        logging.info('Downloading %s%s', artifact_to_download['uri'], ' (simulation)' if env.dry_run else '')
        if not env.dry_run:
            local_artifact_path = nimp.system.try_execute(
                lambda: nimp.artifacts.download_artifact(env.root_dir, artifact_to_download['uri']), OSError
            )

        logging.info(
            'Installing %s in %s%s',
            artifact_to_download['uri'],
            install_directory,
            ' (simulation)' if env.dry_run else '',
        )
        if not env.dry_run:
            nimp.artifacts.install_artifact(local_artifact_path, install_directory)
            shutil.rmtree(local_artifact_path)

        if env.track:
            workspace_status = nimp.system.load_status(env)
            old_revision = (
                workspace_status[env.track][env.platform] if env.platform in workspace_status[env.track] else None
            )
            logging.info(
                'Tracking for %s %s: %s => %s', env.track, env.platform, old_revision, artifact_to_download['revision']
            )
            workspace_status[env.track][env.platform] = artifact_to_download['revision']
            if env.track in ['package', 'staged']:
                if hasattr(env, 'target'):
                    workspace_status[env.track]['variant'] = env.target
                workspace_status[env.track]['path'] = nimp.system.sanitize_path(artifact_to_download['uri'])
                workspace_status[env.track]['name'] = os.path.basename(
                    os.path.normpath(workspace_status[env.track]['path'])
                )
            # if not env.dry_run:
            nimp.system.save_status(env, workspace_status)

        return True

    @staticmethod
    def _find_matching_artifact(
        all_artifacts: list[nimp.artifacts.Artifact],
        exact_revision: str | None,
        minimum_revision: str | None,
        maximum_revision: str | None,
        api_context: git.GitApiContext | None,
    ) -> nimp.artifacts.Artifact:
        # fastpath for exact_revision
        if exact_revision is not None:
            if (artifact := next((a for a in all_artifacts if a['revision'] == exact_revision), None)) is not None:
                return artifact
            raise ValueError('Matching artifact not found')

        # fastpath for maximum_revision
        if maximum_revision is not None:
            if (artifact := next((a for a in all_artifacts if a['revision'] == maximum_revision), None)) is not None:
                return artifact

        if (
            any(git.maybe_git_revision(a['revision']) for a in all_artifacts)
            or (minimum_revision is not None and git.maybe_git_revision(minimum_revision))
            or (maximum_revision is not None and git.maybe_git_revision(maximum_revision))
        ):
            logging.debug("might be looking at git revisions")
            if (
                newest_rev := DownloadFileset._get_git_newest_revision(
                    revisions=[a['revision'] for a in all_artifacts],
                    minimum_revision=minimum_revision,
                    maximum_revision=maximum_revision,
                    api_context=api_context,
                )
            ) is not None:
                return next(a for a in all_artifacts if a['revision'] == newest_rev)

        probably_p4_rev = all(a['revision'].isdigit() for a in all_artifacts)
        if probably_p4_rev:
            iter_: Iterator[int] = iter(int(a['revision']) for a in all_artifacts)
            if minimum_revision:
                minimum_revision_int = int(minimum_revision)
                iter_ = filter(lambda rev: rev >= minimum_revision_int, iter_)

            if maximum_revision:
                maximum_revision_int = int(maximum_revision)
                iter_ = filter(lambda rev: rev <= maximum_revision_int, iter_)

            if (revision := max(iter_, default=None)) is not None:
                revision_str = str(revision)
                return next(a for a in all_artifacts if a['revision'] == revision_str)

        raise ValueError('Matching artifact not found')

    @staticmethod
    def _get_git_newest_revision(
        revisions: list[str],
        minimum_revision: str | None,
        maximum_revision: str | None,
        api_context: git.GitApiContext | None,
    ) -> str | None:
        remote: str | None = None
        if api_context is not None:
            repo: Repository = api_context['instance'].repo_get(
                owner=api_context['repo_owner'],
                repo=api_context['repo_name'],
            )
            remote = repo.clone_url
            logging.debug("Using remote %s from api_context", remote)

        cwd_git_dir = git.get_git_dir()
        logging.debug("CWD git-dir: %s", cwd_git_dir)

        if remote is not None:
            with tempfile.TemporaryDirectory(prefix="nimp_git_") as tmp_git_dir:
                Path(tmp_git_dir).mkdir(parents=True, exist_ok=True)
                subprocess.check_call(['git', 'init', '--bare'], cwd=tmp_git_dir)

                subprocess.check_call(['git', 'remote', 'add', 'origin', remote], cwd=tmp_git_dir)

                # if current workdir contains a git repo, use it as alternate to prevent unnecessary burden on remote
                if cwd_git_dir is not None and git.is_shallow_repository(cwd_git_dir) is False:
                    logging.debug("Add CWD git as bare repository alternate")
                    git.add_alternates(cwd_git_dir, cwd=tmp_git_dir)

                return DownloadFileset._find_git_newest_revision(
                    tmp_git_dir,
                    revisions=revisions,
                    minimum_revision=minimum_revision,
                    maximum_revision=maximum_revision,
                )

        elif cwd_git_dir is not None:
            # no remote, fallback to current git
            return DownloadFileset._find_git_newest_revision(
                cwd_git_dir,
                revisions=revisions,
                minimum_revision=minimum_revision,
                maximum_revision=maximum_revision,
            )

        # no current git. Can't find revisions information
        return None

    @staticmethod
    def _find_git_newest_revision(
        git_dir: str,
        revisions: list[str],
        minimum_revision: str | None,
        maximum_revision: str | None,
    ) -> str | None:
        logging.debug("Find newest revisions in %s", git_dir)
        logging.debug("\trevisions: %s", revisions)

        remotes = git.get_remotes(git_dir)
        logging.debug("Found remote %s in repository %s", remotes, git_dir)

        to_fetch = [*revisions]
        if minimum_revision is not None:
            logging.debug("Filter newest revisions with minimum %s", minimum_revision)
            to_fetch.append(minimum_revision)
        if maximum_revision is not None:
            logging.debug("Filter newest revisions with maximum %s", maximum_revision)
            to_fetch.append(maximum_revision)

        fetch_base_cmd = ['git', 'fetch', '--no-recurse-submodules', '--no-progress']
        for remote in remotes:
            logging.debug("Fetch revision from remote %s", remote)
            if subprocess.call([*fetch_base_cmd, remote, *to_fetch], cwd=git_dir) != 0:
                logging.debug("Failed to fetch revisions from %s", remote)
                # might have failed due to one (or more) unknown ref,
                # try one-by-one and ignore failures
                for rev in to_fetch:
                    if subprocess.call([*fetch_base_cmd, remote, rev], cwd=git_dir) != 0:
                        logging.debug("\tFailed to fetch revision %s", rev)

        if minimum_revision is not None:
            minimum_revision = git.rev_parse_verify(minimum_revision, cwd=git_dir)
            logging.debug("Resolved minimum revision to %s", minimum_revision)
        if maximum_revision is not None:
            maximum_revision = git.rev_parse_verify(maximum_revision, cwd=git_dir)
            logging.debug("Resolved maximum revision to %s", maximum_revision)

        rev_list_base_cmd = ['git', 'rev-list', '--ignore-missing', '--max-count=1', '--topo-order']

        def _get_newest_between(rev_left: str, rev_right: str | None) -> str:
            if rev_right is None:
                return rev_left
            return subprocess.check_output([*rev_list_base_cmd, rev_left, rev_right], text=True).strip()

        # keep track of both to return the potentially un-shortened one
        newest_revision: str | None = None
        newest_resolved_revision: str | None = None
        for revision in revisions:
            logging.debug("Look at revision %s", revision)
            # filter revisions by existing in repo and get the full rev if a short one was provided
            resolved_revision = git.rev_parse_verify(revision, cwd=git_dir)
            logging.debug("\tResolved to %s", resolved_revision)
            if resolved_revision is None:
                continue
            revision = resolved_revision

            if _get_newest_between(resolved_revision, maximum_revision) == resolved_revision:
                logging.debug("\trevision %s is NEWER than maximum %s. Skip it.", revision, maximum_revision)
                continue

            if _get_newest_between(resolved_revision, minimum_revision) == minimum_revision:
                logging.debug("\trevision %s is OLDER than minimum %s. Skip it.", revision, minimum_revision)
                continue

            newest_resolved_revision = _get_newest_between(resolved_revision, newest_resolved_revision)
            if resolved_revision == newest_resolved_revision:
                newest_revision = revision
            logging.debug("newest revision is %s", newest_revision)

        return newest_revision
