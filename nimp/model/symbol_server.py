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


import datetime
import logging
import glob
import os
import shutil

import nimp.system


def configure_symbol_server(env, identifier):
    symbol_server = env.symbol_servers[identifier]

    if isinstance(symbol_server, str):
        symbol_server = {
            "type": identifier,
            "path": symbol_server,
        }

    return SymbolServer(
        server_type = symbol_server["type"],
        server_path = nimp.system.sanitize_path(env.format(symbol_server["path"])),
        platform = env.platform,
        expiration = symbol_server.get("expiration", None),
    )


class SymbolServer:


    def __init__(self, server_type, server_path, platform, expiration):
        self.server_type = server_type
        self.server_path = server_path
        self.platform = platform
        self.expiration = expiration


    def list_symbols(self):
        symbols = []

        if self.server_type == "program":
            symbols += glob.glob(os.path.join(self.server_path, "*.exe", "*"))
            symbols += glob.glob(os.path.join(self.server_path, "*.dll", "*"))
            symbols += glob.glob(os.path.join(self.server_path, "*.pdb", "*"))

        if self.server_type == "shaders":
            if self.platform == "ps4":
                symbols += glob.glob(os.path.join(self.server_path, "*.sdb"))
            if self.platform == "xboxone":
                symbols += glob.glob(os.path.join(self.server_path, "**", "*.pdb"), recursive = True)

        symbols.sort()
        return symbols


    def update_symbols(self, source, dry_run):
        if self.server_type == "shaders":
            logging.info("Uploading from '%s' to '%s'%s", source, self.server_path, " (Simulation)" if dry_run else "")

            all_files = glob.glob(os.path.join(source, "**"), recursive = True)
            all_files = [ path for path in all_files if os.path.isfile(path) ]

            for source_file in all_files:
                destination_file = os.path.join(self.server_path, os.path.relpath(source_file, source))
                logging.info("Copying '%s' to '%s'", source_file, destination_file)

                if not dry_run:
                    os.makedirs(os.path.dirname(destination_file), exist_ok = True)
                    shutil.copyfile(source_file, destination_file)


    def list_symbols_to_clean(self, all_symbols):
        now = datetime.datetime.now()

        symbols_to_clean = []

        if self.server_type == "program":
            for symbol_path in all_symbols:
                symbol_files = glob.glob(os.path.join(symbol_path, "*"))
                if len(symbol_files) == 0: # pylint: disable = len-as-condition
                    symbols_to_clean.append(symbol_path)

                elif self.expiration is not None:
                    modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(symbol_files[0]))
                    if now - modification_time > self.expiration:
                        symbols_to_clean.append(symbol_path)

        if self.server_type == "shaders":
            for symbol_path in all_symbols:
                if self.expiration is not None:
                    modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(symbol_path))
                    if now - modification_time > self.expiration:
                        symbols_to_clean.append(symbol_path)

        return symbols_to_clean


    def clean_symbols(self, symbols_to_clean, dry_run): # pylint: disable = no-self-use
        for symbol_path in symbols_to_clean:
            logging.info("Removing '%s'", symbol_path)
            if not dry_run:
                try:
                    if os.path.isdir(symbol_path):
                        shutil.rmtree(symbol_path)
                    elif os.path.isfile(symbol_path):
                        os.remove(symbol_path)
                except OSError:
                    logging.warning("Failed to remove '%s'", symbol_path, exc_info = True)
