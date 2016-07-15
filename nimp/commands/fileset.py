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
import os.path

import logging

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
        stash_dir = env.format('{root_dir}/.nimp/stash')
        nimp.system.safe_makedirs(stash_dir)

        stash_file = os.path.join(stash_dir, env.fileset)
        nimp.system.safe_delete(stash_file)

        with open(stash_file, 'w') as stash:
            for src, _ in file_mapper():
                src = nimp.system.sanitize_path(src)
                if not os.path.isfile(src):
                    continue
                if src.endswith('.stash'):
                    continue
                md5 = hashlib.md5(src.encode('utf8')).hexdigest()
                os.replace(src, os.path.join(stash_dir, md5))
                logging.info('Stashing %s as %s', src, md5)
                stash.write('%s %s\n' % (md5, src))

        return True

class _Unstash(FilesetCommand):
    ''' Restores a stashed fileset; does not actually use the fileset '''
    def __init__(self):
        super(_Unstash, self).__init__()

    def _run_fileset(self, env, file_mapper):
        stash_dir = env.format('{root_dir}/.nimp/stash')
        stash_file = os.path.join(stash_dir, env.fileset)

        success = True
        with open(stash_file, 'r') as stash:
            for dst in stash.readlines():
                try:
                    md5, dst = dst.strip().split()
                    src = os.path.join(stash_dir, md5)
                    logging.info('Unstashing %s as %s', md5, dst)
                    nimp.system.safe_delete(dst)
                    os.replace(src, dst)
                except Exception as ex:
                    logging.error(ex)
                    success = False
        nimp.system.safe_delete(stash_file)

        return success

