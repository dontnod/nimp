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

'''Command to update the symbol server'''

import os
import shutil

import nimp.command
import nimp.model.symbol_server
import nimp.system


def _list_files(source):
    all_files = []

    for file_path in os.listdir(source):
        file_path = os.path.join(source, file_path)
        if os.path.isdir(file_path):
            all_files.extend(_list_files(file_path))
        else:
            all_files.append(file_path)

    return all_files


def _copy_file(source, destination, dry_run):
    if not dry_run:
        destination_directory = os.path.dirname(destination)
        if not os.path.exists(destination_directory):
            os.makedirs(destination_directory)
        shutil.copyfile(source, destination)


class UpdateSymbolServer(nimp.command.Command):
    '''[DEPRECATED} (use nimp symbol-server) Update the symbol server'''

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'dry_run', 'free_parameters')
        parser.add_argument('--symbol-type', required=True, metavar='<type>', help='Set the type of symbols to upload')
        parser.add_argument('--platform', metavar='<platform>', help='Set the platform to upload symbols for')
        return True

    def is_available(self, env):
        if not hasattr(env, 'symbol_servers'):
            return False, 'symbol_servers is not defined'
        return True, ''

    def run(self, env):
        symbol_server = nimp.model.symbol_server.configure_symbol_server(env, env.symbol_type)

        if hasattr(env, 'is_unreal') and env.is_unreal and symbol_server.server_type == 'shaders':
            symbol_source = '{uproject_dir}/Saved/ShaderDebugInfo/'
            if env.unreal_platform == 'PS4':
                platform_symbol_source = 'SF_PS4/sdb'
            # elif env.unreal_platform == 'PS5':
            #     platform_symbol_source = 'SF_PS5/agsd'
            else:
                platform_symbol_source = env.unreal_platform
            symbol_source += platform_symbol_source
            symbol_source = nimp.system.sanitize_path(env.format(symbol_source))
            symbol_server.update_symbols(symbol_source, env.dry_run)

        return True
