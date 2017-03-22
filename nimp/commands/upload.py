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
''' Uploading related commands '''

import itertools
import logging
import os
import shutil
import zipfile

import nimp.command
import nimp.torrent

class Upload(nimp.command.CommandGroup):
    ''' Uploading commands '''
    def __init__(self):
        super(Upload, self).__init__([_Symbols()])

    def is_available(self, env):
        return True, ''

class _Symbols(nimp.command.Command):
    ''' Uploads build symbols (and binaries!) to a symbol server '''
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
                            action  = 'store_true')
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        # TODO:
        # In order for this step not to be called at the end of a compilation job anymore
        # (rather, triggered somehow once compilation / publishing are done...):
        # gotta insert binaries + symbols zips deployment code (think deploy step) before the below code
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
