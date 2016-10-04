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
''' Publishing related commands '''

import logging
import os
import shutil
import zipfile

import nimp.command
import nimp.torrent

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
    ''' Publishes build symbols (and binaries!) to a symbol server '''
    def __init__(self):
        super(_Symbols, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser,
                                          'platform',
                                          'configuration',
                                          'target',
                                          'revision')
        parser.add_argument('-z',
                            '--compress',
                            help    = 'Compress symbols when uploading',
                            default = False,
                            action  = 'store_true')
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        symbols_to_publish = nimp.system.map_files(env)
        symbols_to_publish.load_set("symbols")
        binaries_to_publish = nimp.system.map_files(env)
        binaries_to_publish.load_set("binaries")
        return nimp.build.upload_symbols(env, _Symbols._chain_symbols_and_binaries(symbols_to_publish(), binaries_to_publish()))

    @staticmethod
    def _chain_symbols_and_binaries(symbols, binaries):
        # sort of itertools.chain, but binaries are pushed only if corresp. symbol is present
        symbol_roots = []
        for symbol in symbols:
            symbol_root, _ = os.path.splitext(symbol[0])
            symbol_roots.append(symbol_root)
            yield symbol
        for binary in binaries:
            binary_root, _ = os.path.splitext(binary[0])
            # (it's always Microsoft platform so OK to just splitext)
            if binary_root in symbol_roots:
                yield binary

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

        return True

    def is_available(self, env):
        return (nimp.system.try_import('BitTornado') is not None,
                ('bittornado python module was not found on your system and is '
                 'required by this command. You can install it with pip3 (give '
                 'bittornado repo url here) '))

    def run(self, env):
        if not env.check_config('binaries_tmp', 'binaries_archive', 'binaries_torrent'):
            return False

        files_to_deploy = nimp.system.map_files(env).to(env.format(env.root_dir))

        for config_or_target in env.configurations:

            config = config_or_target if config_or_target not in ['editor', 'tools'] else 'devel'
            target = config_or_target if config_or_target in ['editor', 'tools'] else 'game'

            tmp = files_to_deploy.override(configuration = config, target = target)
            tmp = tmp.src(env.binaries_tmp)
            tmp.glob("**")

        logging.info("Deploying binaries…")
        if not nimp.system.all_map(nimp.system.robocopy, files_to_deploy()):
            return False

        # Create a Zip file
        archive = nimp.system.sanitize_path(env.format(env.binaries_archive))
        archive_tmp = archive + '.tmp'

        logging.info('Creating Zip file %s…', archive)

        if not os.path.isdir(os.path.dirname(archive)):
            nimp.system.safe_makedirs(os.path.dirname(archive))

        fd = zipfile.ZipFile(archive_tmp, 'w', zipfile.ZIP_DEFLATED)
        publish = nimp.system.map_files(env)
        publish.to('.').load_set('version')
        for src, dst in publish():
            if os.path.isfile(src):
                logging.info('Adding %s as %s', src, dst)
                fd.write(src, dst)
        fd.close()
        shutil.move(archive_tmp, archive)

        # Create a torrent
        torrent = nimp.system.sanitize_path(env.format(env.binaries_torrent))
        torrent_tmp = torrent + '.tmp'

        logging.info('Creating torrent %s…', torrent)

        if not os.path.isdir(os.path.dirname(torrent)):
            nimp.system.safe_makedirs(os.path.dirname(torrent))

        publish = nimp.system.map_files(env)
        publish.src(env.binaries_archive).to(os.path.basename(archive))
        data = nimp.torrent.make_torrent(None, env.torrent_tracker, publish)
        if not data:
            logging.error('Torrent is empty (no files?)')
            return False
        with open(torrent_tmp, 'wb') as fd:
            fd.write(data)
        shutil.move(torrent_tmp, torrent)

        return True

