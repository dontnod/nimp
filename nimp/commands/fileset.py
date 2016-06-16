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
        return self._run_fileset(files_chain)

    @abc.abstractmethod
    def _run_fileset(self, file_mapper):
        pass

class Fileset(nimp.command.CommandGroup):
    ''' Fileset related commands '''
    def __init__(self):
        super(Fileset, self).__init__([_List(),
                                       _Delete()])

    def is_available(self, env):
        return True, ''

class _Delete(FilesetCommand):
    ''' Loads a fileset and delete mapped files '''
    def __init__(self):
        super(_Delete, self).__init__()

    def _run_fileset(self, file_mapper):
        for path, _ in file_mapper():
            logging.info("Deleting %s", path)
            nimp.system.force_delete(path)

        return True

class _List(FilesetCommand):
    ''' Loads a fileset and prints mapped files '''
    def __init__(self):
        super(_List, self).__init__()

    def _run_fileset(self, file_mapper):
        for source, destination in file_mapper():
            logging.info("%s => %s", source, destination)

        return True

