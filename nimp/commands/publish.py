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

''' Publishing related commands '''

import itertools
import logging
import os
import shutil
import zipfile

import nimp.command
import nimp.utils.torrent

class Publish(nimp.command.CommandGroup):
    ''' Publishing commands '''
    def __init__(self):
        super(Publish, self).__init__([_Binaries(),
                                       _Symbols(),
                                       _Version()])

    def is_available(self, env):
        return True, ''

class _Binaries(nimp.command.Command):
    ''' Publishes binaries fileset '''
    def __init__(self):
        super(_Binaries, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser,
                                          'platform',
                                          'configuration',
                                          'target',
                                          'revision')
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        if not env.check_config('binaries_tmp'):
            return False

        files_to_publish = nimp.system.map_files(env)
        files_to_publish.to(env.binaries_tmp).load_set("binaries")
        return nimp.system.all_map(nimp.system.robocopy, files_to_publish())

class _Symbols(nimp.command.Command):
    ''' Publishes symbols fileset '''
    def __init__(self):
        super(_Symbols, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser,
                                          'platform',
                                          'configuration',
                                          'target',
                                          'revision')
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        if not env.check_config('symbols_tmp'):
            return False

        files_to_publish = nimp.system.map_files(env)
        files_to_publish.to(env.symbols_tmp).load_set("symbols")
        return nimp.system.all_map(nimp.system.robocopy, files_to_publish())


class _Version(nimp.command.Command):
    ''' Creates a torrent out of compiled binaries '''
    def __init__(self):
        super(_Version, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser,
                                          'platform',
                                          'target',
                                          'revision')

        parser.add_argument('-l',
                            '--configurations',
                            help    = 'Configurations and targets to deploy',
                            metavar = '<configurations>',
                            nargs = '+')
        parser.add_argument('-s',
                            '--do_symbols',
                            help    = 'Create a torrent out of symbols INSTEAD of binaries',
                            default = False,
                            action  = 'store_true')

        return True

    def is_available(self, env):
        return (nimp.system.try_import('BitTornado') is not None,
                ('bittornado python module was not found on your system and is '
                 'required by this command. You can install it with pip3 (give '
                 'bittornado repo url here) '))

    def run(self, env):

        files_to_deploy = nimp.system.map_files(env).to(env.format(env.root_dir))

        is_data = set(['tiles', 'lights']) & set(env.configurations)

        # If we’re publishing data
        if is_data:
            if not env.check_config('data_archive_for_publish', 'data_torrent'):
                return False
            target_desc = 'tiles' if 'tiles' in env.configurations else 'lights'
            archive_path = env.data_archive_for_publish
            torrent_path = env.data_torrent
            env.dataset = target_desc

        # If we’re publishing binaries (or symbols)
        else:
            if not env.check_config('symbols_tmp' if env.do_symbols else 'binaries_tmp',
                                    'symbols_archive_for_publish' if env.do_symbols else 'binaries_archive_for_publish',
                                    'symbols_torrent' if env.do_symbols else 'binaries_torrent'):
                return False
            target_desc = 'symbols' if env.do_symbols else 'binaries'
            archive_path = env.symbols_archive_for_publish if env.do_symbols else env.binaries_archive_for_publish
            torrent_path = env.symbols_torrent if env.do_symbols else env.binaries_torrent

            for config_or_target in env.configurations:
                config = config_or_target if config_or_target not in ['editor', 'tools'] else 'devel'
                target = config_or_target if config_or_target in ['editor', 'tools'] else 'game'

                tmp = files_to_deploy.override(configuration = config, target = target)
                tmp = tmp.src(env.symbols_tmp if env.do_symbols else env.binaries_tmp)
                tmp.glob("**")

        logging.info('Deploying %s…', target_desc)
        if not nimp.system.all_map(nimp.system.robocopy, files_to_deploy()):
            return False

        archive = _Version._create_zip_file(archive_path, env)
        _Version._create_torrent(archive_path, archive, torrent_path, env)

        return True

    @staticmethod
    def _create_zip_file(archive_path, env):
        archive = nimp.system.sanitize_path(env.format(archive_path))
        archive_tmp = archive + '.tmp'

        logging.info('Creating Zip file %s…', archive)

        if not os.path.isdir(os.path.dirname(archive)):
            nimp.system.safe_makedirs(os.path.dirname(archive))

        publish = nimp.system.map_files(env)
        publish.to('.').load_set('version')
        to_zip_alt, to_zip = itertools.tee(publish())
        all_zips = False
        for src, dst in to_zip_alt:
            if os.path.isfile(src):
                all_zips = True
                if not src.endswith('.zip'):
                    all_zips = False
                    break
        compression = zipfile.ZIP_STORED if all_zips else zipfile.ZIP_DEFLATED
        fd = zipfile.ZipFile(archive_tmp, 'w', compression)
        for src, dst in to_zip:
            if os.path.isfile(src):
                logging.info('Adding %s as %s', src, dst)
                fd.write(src, dst)
        fd.close()
        shutil.move(archive_tmp, archive)
        return archive

    @staticmethod
    def _create_torrent(archive_path, archive, torrent_path, env):
        torrent = nimp.system.sanitize_path(env.format(torrent_path))
        torrent_tmp = torrent + '.tmp'

        logging.info('Creating torrent %s…', torrent)

        if not os.path.isdir(os.path.dirname(torrent)):
            nimp.system.safe_makedirs(os.path.dirname(torrent))

        publish = nimp.system.map_files(env)
        publish.src(archive_path).to(os.path.basename(archive))
        data = nimp.utils.torrent.create(None, env.torrent_tracker, publish)
        if not data:
            logging.error('Torrent is empty (no files?)')
            return False
        with open(torrent_tmp, 'wb') as fd:
            fd.write(data)
        shutil.move(torrent_tmp, torrent)
        return torrent
