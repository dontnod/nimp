# -*- coding: utf-8 -*-
# Copyright © 2014—2016 Dontnod Entertainment

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
''' Deploys binary files from a zipped archives '''

import io
import logging
import os
import os.path
import shutil
import stat
import tempfile
import zipfile

import requests

#from pyremotezip import RemoteZip
# (would be nice, but pyremotezip is python2 for now)

import nimp.command
import nimp.environment
import nimp.system

MAGIC = nimp.system.try_import('magic')

class Deploy(nimp.command.Command):
    ''' Deploys compiled binaries to local directory '''
    def __init__(self):
        super(Deploy, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'revision', 'platform', 'target')

        parser.add_argument('--max-revision',
                            help = 'Find a revision <= to this',
                            metavar = '<revision>')
        parser.add_argument('--min-revision',
                            help = 'Find a revision >= to this',
                            metavar = '<revision>')
        parser.add_argument('-s',
                            '--do_symbols',
                            help    = 'Deploy symbols INSTEAD of binaries',
                            action  = 'store_true')

        return True

    def is_available(self, env):
        if nimp.system.is_windows():
            return True, ''

        return (MAGIC is not None and hasattr(MAGIC, 'from_file'),
                ('The python-magic module was not found on your system and is '
                 'required by this command.'))

    def run(self, env):
        mapper = nimp.system.map_files(env)
        mapper = mapper.to(env.root_dir)

        logging.debug("Deploying version…")

        # Early exit, options harmonizing etc:
        incompatible_options = ((env.max_revision is not None and env.min_revision is not None and int(env.max_revision) < int(env.min_revision))
                                or (env.revision is not None and env.min_revision is not None and int(env.revision) < int(env.min_revision))
                                or (env.max_revision is not None and env.revision is not None and int(env.max_revision) < int(env.revision)))
        if incompatible_options:
            error_message = 'Incompatible options'
            if env.revision is not None:
                error_message += ' - requested revision = %s' % env.revision
            if env.max_revision is not None:
                error_message += ' - specified max revision = %s' % env.max_revision
            if env.min_revision is not None:
                error_message += ' - specified min revision = %s' % env.min_revision
            logging.error(error_message)
            return False
        if env.revision is None and env.max_revision is not None and env.min_revision is not None and int(env.max_revision) == int(env.min_revision):
            env.revision = env.max_revision # speeding things up

        if hasattr(env, 'target') and (set(['tiles', 'lights']) & set(env.target)):
            env.dataset = 'tiles' if 'tiles' in env.target else 'lights'
            archive = env.data_archive_for_deploy
        else:
            archive = env.symbols_archive_for_deploy if env.do_symbols else env.binaries_archive_for_deploy
        revision_info = nimp.system.get_latest_available_revision(env, archive, **vars(env))
        env.revision = revision_info['revision']
        archive_location = revision_info['location']
        if env.revision is None or archive_location is None:
            return False

        # Now decompress the archive
        archive_object = None
        try:
            if revision_info['is_http']:
                # (pyremotezip would be nice here (snippets below), but it's python2 for now)
                # snippets: rz = RemoteZip(archive_location); toc = rz.getTableOfContents(); output = rz.extractFile(toc[2]['filename'])
                get_request = requests.get(archive_location, stream=True)
                # TODO: test get_request.ok and/or get_request.status_code...
                archive_size = int(get_request.headers['content-length'])
                tmp_download_directory = nimp.system.sanitize_path(env.format(os.path.join(env.root_dir, env.game, 'Intermediate', 'Downloads')))
                nimp.system.safe_makedirs(tmp_download_directory) # As NamedTemporaryFile apparently needs an existing dir when the parameter is passed
                archive_object = tempfile.NamedTemporaryFile(prefix='tmp_', suffix='.zip', dir=tmp_download_directory)
                logging.info('Download of %s is starting.', archive_location)
                try:
                    Deploy._custom_copyfileobj(get_request.raw, archive_object, archive_size)
                    logging.info('Download of %s is done!', archive_location)
                except OSError as ex:
                    logging.error('Download of %s has failed: %s', archive_location, ex)
                    raise Exception('Download has failed') from ex
            else:
                archive_object = open(nimp.system.sanitize_path(archive_location), 'rb')
            Deploy._decompress(archive_object, env, handle_zip_of_zips=True)
            nimp.system.save_last_deployed_revision(env)

            return True
        except Exception as ex: #pylint: disable=broad-except
            logging.error('Decompression of archive %s has failed: %s', archive_location, ex)
            return False
        finally:
            if archive_object is not None:
                archive_object.close()

    @staticmethod
    def _decompress(file, env, handle_zip_of_zips=False):
        zip_file = zipfile.ZipFile(file)
        go_deeper = False
        if handle_zip_of_zips:
            go_deeper = True
            for name in zip_file.namelist():
                if not name.endswith('.zip'):
                    go_deeper = False
                    break
        for name in zip_file.namelist():
            if go_deeper:
                Deploy._decompress(io.BytesIO(zip_file.read(name)), env)
            else:
                logging.info('Extracting %s to %s', name, env.root_dir)
                zip_file.extract(name, nimp.system.sanitize_path(env.format(env.root_dir)))
                filename = nimp.system.sanitize_path(os.path.join(env.format(env.root_dir), name))
                Deploy._make_executable_if_needed(filename)

    @staticmethod
    def _custom_copyfileobj(fsrc, fdst, source_size, length=16*1024):
        ''' Custom version of shutil.copyfileobj tailored to add progress logging 
            for our streaming/download/http copyfileobj case '''
        copied = 0
        copied_perc = 0
        download_log_perc_interval = 5
        while 1:
            buf = fsrc.read(length)
            if not buf:
                break
            fdst.write(buf)
            copied += len(buf)
            new_copied_perc = int(copied * 100 / source_size)
            if new_copied_perc >= copied_perc + download_log_perc_interval:
                copied_perc = new_copied_perc
                logging.info('%d%% downloaded', copied_perc)

    @staticmethod
    def _make_executable_if_needed(filename):
        # If this is an executable or a script, make it +x
        if MAGIC is not None:
            filetype = MAGIC.from_file(filename)
            if isinstance(filetype, bytes):
                # Older versions of python-magic return bytes instead of a string
                filetype = filetype.decode('ascii')

            if 'executable' in filetype or 'script' in filetype:
                try:
                    logging.info('Making executable because of file type: %s', filetype)
                    file_stat = os.stat(filename)
                    os.chmod(filename, file_stat.st_mode | stat.S_IEXEC)
                except Exception: #pylint: disable=broad-except
                    pass
