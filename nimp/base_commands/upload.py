# -*- coding: utf-8 -*-
# Copyright (c) 2014-2019 Dontnod Entertainment

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

'''Uploading related commands'''

import itertools
import os

import nimp.command
import nimp.system
import nimp.build


class Upload(nimp.command.CommandGroup):
    '''Uploading commands'''

    def __init__(self):
        super(Upload, self).__init__([_Symbols()])

    def is_available(self, env):
        return True, ''


class _Symbols(nimp.command.Command):
    '''Uploads build symbols (and binaries!) to a symbol server'''

    def __init__(self):
        super(_Symbols, self).__init__()

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'dry_run', 'platform', 'target', 'revision')
        parser.add_argument(
            '-l', '--configurations', help='Configurations and targets to upload', metavar='<configurations>', nargs='+'
        )
        parser.add_argument('-z', '--compress', help='Compress symbols when uploading', action='store_true')

        parser.add_argument(
            '--single-tier', help='Do not use symstore /3 option even if available', action='store_true'
        )

        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        # ps5 shipping has no corresponding symbols, they're in the elf/self unstripped binary file
        has_symbols_inside_binary_file = env.platform in ['ps5']

        iterators = []
        for config_or_target in env.configurations:
            config = config_or_target if config_or_target not in ['editor', 'tools'] else 'devel'
            target = config_or_target if config_or_target in ['editor', 'tools'] else 'game'

            symbols_to_publish = nimp.system.map_files(env)
            symbols_to_publish.root_based = False
            tmp_symbols_to_publish = symbols_to_publish.override(configuration=config, target=target)
            tmp_symbols_to_publish.load_set("symbols")
            binaries_to_publish = nimp.system.map_files(env)
            binaries_to_publish.root_based = False
            tmp_binaries_to_publish = binaries_to_publish.override(configuration=config, target=target)
            tmp_binaries_to_publish.load_set("binaries")

            iterators.append(
                _Symbols._chain_symbols_and_binaries(
                    symbols_to_publish(), binaries_to_publish(), has_symbols_inside_binary_file
                )
            )

        return nimp.build.upload_symbols(
            env, itertools.chain(*iterators), '_'.join(env.configurations), two_tier_mode=not env.single_tier
        )

    @staticmethod
    def _chain_symbols_and_binaries(symbols, binaries, has_symbols_inside_binary_file=False):
        # sort of itertools.chain, but binaries are pushed only if corresp. symbol is present
        symbol_roots = []
        for symbol_src, __symbol_dest in symbols:
            symbol_root, _ = os.path.splitext(symbol_src)
            symbol_roots.append(symbol_root)
            yield symbol_src
        for binary_src, __binary_dest in binaries:
            # (it's always Microsoft platform so OK to just splitext)
            binary_root, _ = os.path.splitext(binary_src)
            # symbols inside binaries, no symbols, just yield binaries and no corresponding symbols
            if has_symbols_inside_binary_file and os.path.isfile(binary_src):
                yield binary_src
            elif binary_root in symbol_roots:
                yield binary_src
