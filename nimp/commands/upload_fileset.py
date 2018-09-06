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
''' Command to uUpload a fileset to the artifact repository '''

import logging
import os
import zipfile

import nimp.command


class UploadFileset(nimp.command.Command):
    ''' Uploads a fileset to the artifact repository '''

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'revision', 'free_parameters')
        parser.add_argument('fileset', metavar = '<fileset>', help = 'fileset to upload')
        parser.add_argument('--archive', default = False, action = 'store_true', help = 'upload the files as a zip archive')
        parser.add_argument('--compress', default = False, action = 'store_true', help = 'if uploading as an archive, compress it')
        parser.add_argument('--torrent', default = False, action = 'store_true', help = 'create a torrent for the uploaded fileset')
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        if env.torrent and nimp.system.try_import('BitTornado') is None:
            logging.error('Failed to import BitTornado module (required for torrent option)')
            return False

        output_path = env.artifact_repository_destination + '/' + env.artifact_collection[env.fileset]
        output_path = nimp.system.sanitize_path(env.format(output_path))

        logging.info('Listing files for %s', output_path)
        file_mapper = nimp.system.map_files(env)
        file_mapper.load_set(env.fileset)
        all_files = list(file_mapper())

        if (len(all_files) == 0) or (all_files == [(".", None)]):
            raise RuntimeError('Found no files to upload')

        # Normalize and sort paths to have a deterministic result across systems
        all_files = ((src.replace('\\', '/'), dst.replace('\\', '/')) for src, dst in all_files)
        all_files = list(sorted(set(all_files)))

        logging.info('Uploading to %s', output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok = True)
        nimp.system.try_execute(lambda: nimp.artifacts.create_artifact(output_path, all_files, env.archive, env.compress), (OSError, ValueError, zipfile.BadZipFile))
        if env.torrent:
            logging.info('Creating torrent for %s', output_path)
            nimp.system.try_execute(lambda: nimp.artifacts.create_torrent(output_path), OSError)

        return True
