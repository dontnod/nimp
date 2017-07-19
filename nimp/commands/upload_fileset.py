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
        nimp.command.add_common_arguments(parser, 'platform', 'configuration', 'target', 'revision', 'free_parameters')
        parser.add_argument('fileset', metavar = '<fileset>', help = 'fileset to upload')
        parser.add_argument('--archive', default = False, action = 'store_true', help = 'upload the files as a zip archive')
        parser.add_argument('--compress', default = False, action = 'store_true', help = 'if uploading as an archive, compress it')
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        output_path = env.artifact_repository_destination + '/' + env.artifact_collection[env.fileset]['temporary']
        if env.archive:
            files_to_deploy = nimp.system.map_files(env)
            files_to_deploy.to('.').load_set(env.fileset)
            compression = zipfile.ZIP_DEFLATED if env.compress else zipfile.ZIP_STORED
            success, archive_path = UploadFileset._create_archive(env, output_path, files_to_deploy(), compression)
        else:
            files_to_deploy = nimp.system.map_files(env)
            files_to_deploy.to(output_path).load_set(env.fileset)
            success = nimp.system.all_map(nimp.system.robocopy, files_to_deploy())
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
                    logging.info('Adding %s as %s', src, dst)
                    archive_file.write(src, dst)
                    is_empty = False

        if is_empty:
            logging.error("Archive is empty")
            os.remove(archive_tmp)
            return False, None
        shutil.move(archive_tmp, archive_path)
        return True, archive_path