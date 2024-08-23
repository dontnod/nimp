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

import copy
import logging
import os
import shutil
from pathlib import PurePosixPath

import nimp.artifacts
import nimp.command
import nimp.system


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

    def run(self, env):
        api_context = nimp.utils.git.initialize_gitea_api_context(env)

        artifacts_source = env.artifact_repository_source
        if env.prefer_http:
            artifacts_http_source = getattr(env, 'artifact_http_repository_source', None)
            if artifacts_http_source:
                artifacts_source = artifacts_http_source
            else:
                logging.warning('prefer-http provided but no artifact_http_repository_source in configuration')

        artifact_uri_pattern = artifacts_source.rstrip('/') + '/' + env.artifact_collection[env.fileset]

        install_directory = env.root_dir
        if env.destination:
            install_directory = str(PurePosixPath(install_directory) / env.format(env.destination))

        format_arguments = copy.deepcopy(vars(env))
        format_arguments['revision'] = '*'
        logging.info('Searching %s', artifact_uri_pattern.format(**format_arguments))
        all_artifacts = nimp.system.try_execute(
            lambda: nimp.artifacts.list_artifacts(artifact_uri_pattern, format_arguments, api_context), OSError
        )
        artifact_to_download = DownloadFileset._find_matching_artifact(
            all_artifacts, env.revision, env.min_revision, env.max_revision, api_context
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

    # TODO: Handle revision comparison when identified by a hash
    @staticmethod
    def _find_matching_artifact(all_artifacts, exact_revision, minimum_revision, maximum_revision, api_context):
        all_artifacts = sorted(all_artifacts, key=lambda artifact: int(artifact['sortable_revision'], 16), reverse=True)
        has_revision_input = exact_revision or minimum_revision or maximum_revision

        if api_context:
            exact_revision = nimp.utils.git.get_gitea_commit_timestamp(api_context, exact_revision)
            minimum_revision = nimp.utils.git.get_gitea_commit_timestamp(api_context, minimum_revision)
            maximum_revision = nimp.utils.git.get_gitea_commit_timestamp(api_context, maximum_revision)
            revision_not_found = not exact_revision and not minimum_revision and not maximum_revision
            if has_revision_input and revision_not_found:
                raise ValueError('Searched commit not found on gitea repo')

        if not api_context and (has_revision_input is not None and not has_revision_input.isdigit()):
            raise ValueError(
                'Revision seems to be a git commit hash but missing gitea api information. Please check project_branches in project configuration.'
            )

        try:
            if exact_revision is not None:
                return next(a for a in all_artifacts if a['sortable_revision'] == exact_revision)
            if minimum_revision is not None and maximum_revision is not None:
                return next(
                    a
                    for a in all_artifacts
                    if int(a['sortable_revision']) >= int(minimum_revision)
                    and int(a['sortable_revision']) <= int(maximum_revision)
                )
            if minimum_revision is not None:
                return next(a for a in all_artifacts if int(a['sortable_revision']) >= int(minimum_revision))
            if maximum_revision is not None:
                return next(a for a in all_artifacts if int(a['sortable_revision']) <= int(maximum_revision))
            return next(a for a in all_artifacts)
        except StopIteration:
            raise ValueError('Matching artifact not found')
