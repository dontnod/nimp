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


import logging

import nimp.command
import nimp.model.symbol_server


class SymbolServer(nimp.command.CommandGroup):
    ''' Commands for the symbol servers '''


    def __init__(self):
        super().__init__([ Status(), Update(), Clean() ])


    def is_available(self, env):
        if not hasattr(env, 'symbol_servers'):
            return False, 'Symbol servers are not configured'
        return True, ''


    def configure_arguments(self, env, parser):
        parser.add_argument('--identifier', required = True, metavar = '<type>', help = 'select a symbol server from the configuration')
        parser.add_argument('--platform', required = True, metavar = '<platform>', help = 'set the platform for the symbols')

        super().configure_arguments(env, parser)


class Status(nimp.command.Command):
    ''' Show the symbol server status '''


    def configure_arguments(self, env, parser):
        return True


    def is_available(self, env):
        if not hasattr(env, 'symbol_servers'):
            return False, 'Symbol servers are not configured'
        return True, ''


    def run(self, env):
        symbol_server = nimp.model.symbol_server.configure_symbol_server(env, env.identifier)

        logging.info("Status for symbol server at '%s'", symbol_server.server_path)

        all_symbols = symbol_server.list_symbols()
        logging.info("Symbol count: %s", len(all_symbols))

        return True


class Update(nimp.command.Command):
    ''' Update the symbol server '''


    def configure_arguments(self, env, parser):
        parser.add_argument("--simulate", action = "store_true", help = "perform the command as a simulation")
        return True


    def is_available(self, env):
        if not hasattr(env, 'symbol_servers'):
            return False, 'Symbol servers are not configured'
        return True, ''


    def run(self, env):
        symbol_server = nimp.model.symbol_server.configure_symbol_server(env, env.identifier)

        if symbol_server.server_type == 'shaders' and env.project_type == 'UE4':
            symbol_source = '{root_dir}/{game}/Saved/ShaderDebugInfo'
            symbol_source += '/' + ('SF_PS4/sdb' if env.ue4_platform == 'PS4' else env.ue4_platform)
            symbol_source = nimp.system.sanitize_path(env.format(symbol_source))
            symbol_server.update_symbols(symbol_source, env.simulate)

        return True



class Clean(nimp.command.Command):
    ''' Clean the symbol server '''


    def configure_arguments(self, env, parser):
        parser.add_argument("--simulate", action = "store_true", help = "perform the command as a simulation")
        return True


    def is_available(self, env):
        if not hasattr(env, 'symbol_servers'):
            return False, 'Symbol servers are not configured'
        return True, ''


    def run(self, env):
        symbol_server = nimp.model.symbol_server.configure_symbol_server(env, env.identifier)

        logging.info("Cleaning symbol server at '%s'%s", symbol_server.server_path, " (Simulation)" if env.simulate else "")

        all_symbols = symbol_server.list_symbols()
        symbols_to_clean = symbol_server.list_symbols_to_clean(all_symbols)
        symbol_server.clean_symbols(symbols_to_clean, env.simulate)

        logging.info("Symbol count: %s => %s", len(all_symbols), len(all_symbols) - len(symbols_to_clean))

        return True
