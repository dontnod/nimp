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
''' Fileset related commands '''

import abc
import hashlib
import logging
import os
import shutil

import nimp.command
import nimp.system

class FilesetCommand(nimp.command.Command):
    ''' Perforce command base class '''

    def __init__(self):
        super(FilesetCommand, self).__init__()

    def configure_arguments(self, env, parser):
        parser.add_argument('fileset',
                            help    = 'Set name to load (e.g. binaries, version...)',
                            metavar = '<fileset>')

        nimp.command.add_common_arguments(parser,
                                          'platform',
                                          'configuration',
                                          'target',
                                          'free_parameters')
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        files = nimp.system.map_files(env)
        files_chain = files
        files_chain.load_set(env.fileset)
        return self._run_fileset(env, files_chain)

    @abc.abstractmethod
    def _run_fileset(self, env, file_mapper):
        pass

class Fileset(nimp.command.CommandGroup):
    ''' Fileset related commands '''
    def __init__(self):
        super(Fileset, self).__init__([_List(),
                                       _Delete(),
                                       _Stash(),
                                       _Unstash(),])

    def is_available(self, env):
        return True, ''

class _Delete(FilesetCommand):
    ''' Loads a fileset and delete mapped files '''
    def __init__(self):
        super(_Delete, self).__init__()

    def _run_fileset(self, env, file_mapper):
        for path, _ in file_mapper():
            logging.info("Deleting %s", path)
            nimp.system.safe_delete(path)

        return True

class _List(FilesetCommand):
    ''' Loads a fileset and prints mapped files '''
    def __init__(self):
        super(_List, self).__init__()

    def _run_fileset(self, env, file_mapper):
        for source, destination in file_mapper():
            logging.info("%s => %s", source, destination)

        return True

class _Stash(FilesetCommand):
    ''' Loads a fileset and moves files out of the way '''
    def __init__(self):
        super(_Stash, self).__init__()

    def _run_fileset(self, env, file_mapper):
        stash_name = env.format('{fileset}-{platform}-{target}-{configuration}')
        stash_directory = env.format('{root_dir}/.nimp/stash/' + stash_name)

        if os.path.exists(stash_directory):
            logging.info('Removing previous stash %s', stash_name)
            shutil.rmtree(stash_directory)

        logging.info('Creating stash %s', stash_name)
        os.makedirs(stash_directory)
        with open(os.path.join(stash_directory, '.stash.txt'), 'w') as stash_file:
            for src, _ in file_mapper():
                if os.path.isfile(src):
                    src_hash = hashlib.md5(src.encode('utf8')).hexdigest()
                    logging.info('Stashing %s as %s', src, src_hash)
                    shutil.move(src, os.path.join(stash_directory, src_hash))
                    stash_file.write('%s %s\n' % (src_hash, src))

        return True

class _Unstash(FilesetCommand):
    ''' Restores a stashed fileset; does not actually use the fileset '''
    def __init__(self):
        super(_Unstash, self).__init__()

    def _run_fileset(self, env, file_mapper):
        stash_name = env.format('{fileset}-{platform}-{target}-{configuration}')
        stash_directory = env.format('{root_dir}/.nimp/stash/' + stash_name)

        if not os.path.exists(stash_directory):
            raise RuntimeError('Stash {stash_name} does not exist'.format(**locals()))

        logging.info('Applying stash %s', stash_name)
        success = True
        with open(os.path.join(stash_directory, '.stash.txt'), 'r') as stash_file:
            for dst in stash_file.readlines():
                try:
                    md5, dst = dst.strip().split()
                    src = os.path.join(stash_directory, md5)
                    logging.info('Unstashing %s as %s', md5, dst)
                    os.makedirs(os.path.dirname(dst), exist_ok = True)
                    if os.path.exists(dst):
                        os.remove(dst)
                    shutil.move(src, dst)
                except OSError as exception:
                    logging.error(exception)
                    success = False

        if success == False:
            raise RuntimeError('Unstash failed')

        logging.info('Removing stash %s', stash_name)
        shutil.rmtree(stash_directory)

        return True
