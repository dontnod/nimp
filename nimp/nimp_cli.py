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
''' Nimp entry point '''

import logging
import os
import platform
import sys
import time
import traceback

import nimp.command
import nimp.commands
import nimp.environment
import nimp.system
import nimp.unreal

sys.dont_write_bytecode = 1

if 'MSYS_NT' in platform.system():
    raise NotImplementedError('MSYS Python is not supported; please use MimGW Python instead')

def _clean_environment_variables():
    # Some Windows tools don’t like “duplicate” environment variables, i.e.
    # where only the case differs; we remove any lowercase version we find.
    # The loop is O(n²) but we don’t have that many entries so it’s all right.
    env_vars = [x.lower() for x in os.environ.keys()]
    for dupe in set([x for x in env_vars if env_vars.count(x) > 1]):
        dupelist = sorted([x for x in os.environ.keys() if x.lower() == dupe ])
        logging.warning("Fixing duplicate environment variable: " + '/'.join(dupelist))
        for duplicated in dupelist[1:]:
            del os.environ[duplicated]
    # … But in some cases (Windows Python) the duplicate variables are masked
    # by the os.environ wrapper, so we do it another way to make sure there
    # are no dupes:
    for key in sorted(os.environ.keys()):
        val = os.environ[key]
        del os.environ[key]
        os.environ[key] = val

def main(argv = None):
    ''' Nimp entry point '''
    if argv is None:
        argv = sys.argv

    start = time.time()

    result = 0
    try:
        if nimp.system.is_windows():
            nimp_monitor = nimp.system.NimpMonitor()
            nimp_monitor.start()

        _clean_environment_variables()

        nimp.environment.Environment.config_loaders += [nimp.unreal.load_config]

        argument_loaders = [nimp.system.load_arguments,
                            nimp.command.load_arguments,
                            nimp.unreal.load_arguments]

        nimp.environment.Environment.argument_loaders += argument_loaders

        result = nimp.environment.Environment().run(argv)

    except KeyboardInterrupt:
        logging.info("Program interrupted. (Ctrl-C)")
        traceback.print_exc()
        result = 1
    except SystemExit:
        result = 1
    finally:
        if nimp.system.is_windows():
            nimp_monitor.stop()

    end = time.time()
    logging.info("Command took %f seconds.", end - start)

    return result

if __name__ == "__main__":
    sys.exit(main())

