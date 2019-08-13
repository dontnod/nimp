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


def configure_symbol_server(env, identifier):
    symbol_server = env.symbol_servers[identifier]

    if isinstance(symbol_server, str):
        return { "path": symbol_server }
    return symbol_server


def list_symbols(path):
    symbols = []
    symbols += glob.glob(os.path.join(path, "*.exe", "*"))
    symbols += glob.glob(os.path.join(path, "*.dll", "*"))
    symbols += glob.glob(os.path.join(path, "*.pdb", "*"))

    symbols.sort()

    return symbols


def list_symbols_to_clean(all_symbols, expiration):
    now = datetime.datetime.now()

    symbols_to_clean = []
    for symbol_path in all_symbols:
        symbol_files = glob.glob(os.path.join(symbol_path, "*"))
        if len(symbol_files) == 0: # pylint: disable = len-as-condition
            symbols_to_clean.append(symbol_path)

        elif expiration is not None:
            modification_time = datetime.datetime.fromtimestamp(os.path.getmtime(symbol_files[0]))
            if now - modification_time > expiration:
                symbols_to_clean.append(symbol_path)

    return symbols_to_clean


def clean_symbols(symbols_to_clean, simulate):
    for symbol_path in symbols_to_clean:
        logging.info("Removing '%s'", symbol_path)
        if not simulate:
            try:
                shutil.rmtree(symbol_path)
            except OSError:
                logging.warning("Failed to remove '%s'", symbol_path, exc_info = True)
