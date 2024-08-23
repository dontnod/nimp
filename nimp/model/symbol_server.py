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
            "path": symbol_server,
        }
    default_expiration = env.symbol_servers.get('expiration', None)
    expiration = symbol_server.get("expiration", symbol_server.get("expiration", default_expiration))
    if expiration is not None:
        expiration = datetime.timedelta(int(expiration))

    return SymbolServer(
        env=env,
        server_type=identifier,
        server_path=nimp.system.sanitize_path(env.format(symbol_server["path"])),
        platform=env.platform,
        expiration=expiration,
    )


class ServerType:
    def __init__(self, server_type):
        self.is_shaders = server_type in ["shaders"]
        self.is_program = server_type in ["program"]


class SymbolServer:
    def __init__(self, env, server_type, server_path, platform, expiration):
        self.env = env
        self.server_type = ServerType(server_type)
        self.server_path = server_path
        self.platform = platform
        self.expiration = expiration

    def list_symbols(self):
        symbols = []

        if self.server_type.is_program:
            symbols += glob.glob(os.path.join(self.server_path, "*.exe", "*"))
            symbols += glob.glob(os.path.join(self.server_path, "*.dll", "*"))
            symbols += glob.glob(os.path.join(self.server_path, "*.pdb", "*"))

        if self.server_type.is_shaders:
            if self.env.is_sony_platform:
                symbols += glob.glob(os.path.join(self.server_path, "*.sdb"), recursive=True)
                symbols += glob.glob(os.path.join(self.server_path, "*.agsd"), recursive=True)
                symbols += glob.glob(os.path.join(self.server_path, "**", "*.sdb"), recursive=True)
                symbols += glob.glob(os.path.join(self.server_path, "**", "*.agsd"), recursive=True)
            if self.env.is_microsoft_platform:
                symbols += glob.glob(os.path.join(self.server_path, "*.pdb"), recursive=True)
                symbols += glob.glob(os.path.join(self.server_path, "**", "*.pdb"), recursive=True)
            if self.env.is_nintendo_platform:
                symbols += glob.glob(os.path.join(self.server_path, "*.glslcoutput"), recursive=True)
                symbols += glob.glob(os.path.join(self.server_path, "**", "*.glslcoutput"), recursive=True)

        symbols.sort()
        return symbols

    def update_symbols(self, source, dry_run):
        if self.server_type.is_shaders:
            logging.info("Uploading from '%s' to '%s'%s", source, self.server_path, " (Simulation)" if dry_run else "")

            all_files = glob.glob(os.path.join(source, "**"), recursive=True)
            all_files = [path for path in all_files if os.path.isfile(path)]

            for source_file in all_files:
                destination_file = os.path.join(self.server_path, os.path.relpath(source_file, source))
                logging.info("Copying '%s' to '%s'", source_file, destination_file)

                if not dry_run:
                    os.makedirs(os.path.dirname(destination_file), exist_ok=True)
                    shutil.copyfile(source_file, destination_file)

    def list_symbols_to_clean(self, all_symbols):
        now = datetime.datetime.now()

        symbols_to_clean = []

        if self.server_type.is_program:
            for symbol_path in all_symbols:
                symbol_files = glob.glob(os.path.join(symbol_path, "*"))
                if len(symbol_files) == 0:  # pylint: disable = len-as-condition
                    symbols_to_clean.append(symbol_path)
                    logging.debug(f"Adding for delete: {symbol_path}")

                elif self.expiration is not None:
                    modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(symbol_files[0]))
                    if now - modification_time > self.expiration:
                        symbols_to_clean.append(symbol_path)
                        logging.debug(f"Adding for delete: {symbol_path}")

        if self.server_type.is_shaders:
            for symbol_path in all_symbols:
                if self.expiration is not None:
                    modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(symbol_path))
                    if now - modification_time > self.expiration:
                        symbols_to_clean.append(symbol_path)
                        logging.debug(f"Adding for delete: {symbol_path}")

        return symbols_to_clean

    @staticmethod
    def clean_symbols(symbols_to_clean, dry_run):  # pylint: disable = no-self-use
        for symbol_path in symbols_to_clean:
            nimp.system.try_remove(symbol_path, dry_run)
