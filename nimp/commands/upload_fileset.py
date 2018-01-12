# -*- coding: utf-8 -*-
# Copyright © 2014—2017 Dontnod Entertainment

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
''' Uploads a fileset to the artifact repository '''

import logging
import os
import shutil
import zipfile

import nimp.command


class UploadFileset(nimp.command.Command):
    ''' Uploads a fileset to the artifact repository '''
    def __init__(self):
        super(UploadFileset, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'platform', 'revision', 'free_parameters')
        parser.add_argument('fileset', metavar = '<fileset>', help = 'fileset to upload')
        parser.add_argument('-c', '--configuration_list', metavar = '<target/configuration>', nargs = '+', help = 'target and configuration pairs to upload')
        parser.add_argument('--archive', default = False, action = 'store_true', help = 'upload the files as a zip archive')
        parser.add_argument('--compress', default = False, action = 'store_true', help = 'if uploading as an archive, compress it')
        parser.add_argument('--torrent', default = False, action = 'store_true', help = 'create a torrent for the uploaded fileset')
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        if env.torrent and nimp.system.try_import('BitTornado') is None:
            logging.error('bittornado python module is required but was not found')
            return False

        output_path = env.artifact_repository_destination + '/' + env.artifact_collection[env.fileset]
        files_to_upload = nimp.system.map_files(env)

        if not env.configuration_list:
            files_to_upload.to('.' if env.archive else output_path + '.tmp').load_set(env.fileset)
        else:
            if len(env.configuration_list) == 1:
                env.target, env.configuration = env.configuration_list[0].split('/')
            for target_configuration_pair in env.configuration_list:
                if '/' in target_configuration_pair:
                    target, configuration = target_configuration_pair.split('/')
                else: # Allow specifying only a target or a configuration, deducing the other
                    configuration = target_configuration_pair if target_configuration_pair not in ['editor', 'tools'] else 'devel'
                    target = target_configuration_pair if target_configuration_pair in ['editor', 'tools'] else 'game'
                files_override = files_to_upload.override(configuration = configuration, target = target)
                files_override.to('.' if env.archive else output_path + '.tmp').load_set(env.fileset)

        output_path = nimp.system.sanitize_path(env.format(output_path))

        if env.archive:
            archive_path = UploadFileset._create_archive(output_path, set(files_to_upload()), env.compress)
            if env.torrent:
                torrent_files = nimp.system.map_files(env)
                torrent_files.src(os.path.dirname(archive_path)).to('.').glob(os.path.basename(archive_path))
                UploadFileset._create_torrent(output_path, torrent_files, env.torrent_tracker)

        else:
            copy_success = nimp.system.all_map(nimp.system.robocopy, set(files_to_upload()))
            if not copy_success:
                raise RuntimeError('Copy failed')
            shutil.rmtree(output_path, ignore_errors = True)
            shutil.move(output_path + '.tmp', output_path)
            if env.torrent:
                torrent_files = nimp.system.map_files(env)
                torrent_files.src(output_path).to('.').glob('**')
                UploadFileset._create_torrent(output_path, torrent_files, env.torrent_tracker)

        return True

    @staticmethod
    def _create_archive(archive_path, file_collection, compress):
        archive_path = nimp.system.sanitize_path(archive_path)
        if not archive_path.endswith('.zip'):
            archive_path += '.zip'
        compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED

        logging.info('Creating zip archive %s…', archive_path)

        if not os.path.isdir(os.path.dirname(archive_path)):
            nimp.system.safe_makedirs(os.path.dirname(archive_path))

        is_empty = True
        with zipfile.ZipFile(archive_path + '.tmp', 'w', compression = compression) as archive_file:
            for src, dst in file_collection:
                if os.path.isfile(src):
                    logging.debug('Adding %s as %s', src, dst)
                    archive_file.write(src, dst)
                    is_empty = False

        if is_empty:
            raise RuntimeError('Archive is empty')

        shutil.move(archive_path + '.tmp', archive_path)
        return archive_path

    @staticmethod
    def _create_torrent(torrent_path, file_collection, torrent_tracker):
        torrent_path = nimp.system.sanitize_path(torrent_path)
        if not torrent_path.endswith('.torrent'):
            torrent_path += '.torrent'
        torrent_tmp = torrent_path + '.tmp'

        logging.info('Creating torrent %s…', torrent_path)

        if not os.path.isdir(os.path.dirname(torrent_path)):
            nimp.system.safe_makedirs(os.path.dirname(torrent_path))

        data = nimp.utils.torrent.create(None, torrent_tracker, file_collection)
        if not data:
            raise RuntimeError('Torrent is empty')

        with open(torrent_tmp, 'wb') as torrent_file:
            torrent_file.write(data)
        shutil.move(torrent_tmp, torrent_path)
