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

        if len(env.configuration_list) == 1:
            env.target, env.configuration = env.configuration_list[0].split('/')
        output_path = env.artifact_repository_destination + '/' + env.artifact_collection[env.fileset]

        files_to_deploy = nimp.system.map_files(env)
        for target_configuration_pair in env.configuration_list:
            if '/' in target_configuration_pair:
                target, configuration = target_configuration_pair.split('/')
            else: # Allow specifying only a target or a configuration, deducing the other
                configuration = target_configuration_pair if target_configuration_pair not in ['editor', 'tools'] else 'devel'
                target = target_configuration_pair if target_configuration_pair in ['editor', 'tools'] else 'game'
            files_override = files_to_deploy.override(configuration = configuration, target = target)
            files_override.to('.' if env.archive else output_path).load_set(env.fileset)

        if env.archive:
            compression = zipfile.ZIP_DEFLATED if env.compress else zipfile.ZIP_STORED
            success, archive_path = UploadFileset._create_archive(env, output_path, files_to_deploy(), compression)
            if success and env.torrent:
                torrent_files = nimp.system.map_files(env)
                torrent_files.src(archive_path).to(os.path.basename(archive_path))
                success = UploadFileset._create_torrent(env, output_path, torrent_files)
        else:
            success = nimp.system.all_map(nimp.system.robocopy, files_to_deploy())
            if success and env.torrent:
                torrent_files = nimp.system.map_files(env)
                torrent_files.src(output_path).load_set(env.fileset)
                success = UploadFileset._create_torrent(env, output_path, torrent_files)
        return success

    @staticmethod
    def _create_archive(env, archive_path, file_collection, compression):
        archive_path = nimp.system.sanitize_path(env.format(archive_path))
        if not archive_path.endswith('.zip'):
            archive_path += '.zip'
        archive_tmp = archive_path + '.tmp'

        logging.info('Creating zip archive %s…', archive_path)

        if not os.path.isdir(os.path.dirname(archive_path)):
            nimp.system.safe_makedirs(os.path.dirname(archive_path))

        is_empty = True
        with zipfile.ZipFile(archive_tmp, 'w', compression = compression) as archive_file:
            for src, dst in file_collection:
                if os.path.isfile(src):
                    logging.debug('Adding %s as %s', src, dst)
                    archive_file.write(src, dst)
                    is_empty = False

        if is_empty:
            logging.error("Archive is empty")
            os.remove(archive_tmp)
            return False, None
        shutil.move(archive_tmp, archive_path)
        return True, archive_path

    @staticmethod
    def _create_torrent(env, torrent_path, file_collection):
        torrent_path = nimp.system.sanitize_path(env.format(torrent_path))
        if not torrent_path.endswith('.torrent'):
            torrent_path += '.torrent'
        torrent_tmp = torrent_path + '.tmp'

        logging.info('Creating torrent %s…', torrent_path)

        if not os.path.isdir(os.path.dirname(torrent_path)):
            nimp.system.safe_makedirs(os.path.dirname(torrent_path))

        data = nimp.utils.torrent.create(None, env.torrent_tracker, file_collection)
        if not data:
            logging.error('Torrent is empty')
            return False
        with open(torrent_tmp, 'wb') as torrent_file:
            torrent_file.write(data)
        shutil.move(torrent_tmp, torrent_path)
        return True