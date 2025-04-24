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

'''Command to uUpload a fileset to the artifact repository'''

import logging
import os
import shutil
import zipfile

import nimp.artifacts
import nimp.command


def _try_remove(file_path, dry_run):
    if os.path.isdir(file_path):
        logging.info('Removing %s', file_path)
        if not dry_run:
            shutil.rmtree(file_path)
    if os.path.isfile(file_path):
        logging.info('Removing %s', file_path)
        if not dry_run:
            os.remove(file_path)


class UploadFileset(nimp.command.Command):
    '''Uploads a fileset to the artifact repository'''

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'dry_run', 'revision', 'slice_job', 'free_parameters')
        parser.add_argument('--archive', action='store_true', help='upload the files as a zip archive')
        parser.add_argument('--compress', action='store_true', help='if uploading as an archive, compress it')
        parser.add_argument('--torrent', action='store_true', help='create a torrent for the uploaded fileset')
        parser.add_argument('--hash', metavar='<hashlib>', default=None, help='create a hash for the uploaded fs')
        parser.add_argument('--force', action='store_true', help='if the artifact already exists, overwrite it')
        parser.add_argument('fileset', metavar='<fileset>', help='fileset to upload')
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        if env.torrent:
            nimp.artifacts.ensure_can_create_torrent()

        if env.torrent and not hasattr(env, 'torrent_tracker_announce'):
            env.torrent_tracker_announce = None

        # load fileset 1st, as it can affect the nimp environment
        file_mapper = nimp.system.FileMapper(None, vars(env))
        file_mapper.load_set(env.fileset)

        artifact_path = f'{file_mapper.artifact_repository_destination}/{file_mapper.artifact_collection[env.fileset]}'
        if env.slice_job_index and env.slice_job_count:
            artifact_path = f'{artifact_path}/slice-{env.slice_job_index}-of-{env.slice_job_count}'
        artifact_path = nimp.system.sanitize_path(env.format(artifact_path))

        if os.path.isfile(artifact_path + '.zip') or os.path.isdir(artifact_path):
            if not env.force:
                raise ValueError('Artifact already exists: %s' % artifact_path)
            else:
                _try_remove(artifact_path + '.torrent', env.dry_run)
                _try_remove(artifact_path + '.zip', env.dry_run)
                _try_remove(artifact_path, env.dry_run)

        logging.info('Listing files for %s', artifact_path)
        all_files = file_mapper.to_list(env.root_dir if file_mapper.root_based else '.', '.')

        if not all_files:
            raise RuntimeError('Found no files to upload')

        logging.info('Uploading to %s', artifact_path)
        if not env.dry_run:
            os.makedirs(os.path.dirname(artifact_path), exist_ok=True)
        nimp.system.try_execute(
            lambda: nimp.artifacts.create_artifact(artifact_path, all_files, env.archive, env.compress, env.dry_run),
            (OSError, ValueError, zipfile.BadZipFile),
        )
        if env.torrent:
            logging.info('Creating torrent for %s', artifact_path)
            nimp.system.try_execute(
                lambda: nimp.artifacts.create_torrent(artifact_path, env.torrent_tracker_announce, env.dry_run), OSError
            )
        if env.hash is not None:
            logging.info(f'Creating hash for {artifact_path}')
            nimp.artifacts.create_hash(artifact_path, env.hash, env.dry_run)

        return True
