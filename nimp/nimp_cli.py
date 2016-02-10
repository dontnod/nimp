#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import sys
sys.dont_write_bytecode = 1

import inspect
import time
import traceback
import platform
import codecs

from nimp import modules
from nimp.modules.module import *
from nimp.utilities.inspection import *
from nimp.utilities.environment import *

if 'MSYS_NT' in platform.system():
    raise NotImplementedError('MSYS Python is not supported; please use MimGW Python instead')

def main():
    t0 = time.time()

    result = 0
    try:
        if is_windows():
            monitor_parent_process()

        module_instances = get_dependency_sorted_instances(modules, Module)

        if module_instances is None:
            log_error("Unable to satisfy module dependencies.")
            return 1

        env = Environment()
        setattr(env, 'modules', module_instances)

        for module_it in module_instances:
            if not module_it.load(env):
                result = -1
                break

    except KeyboardInterrupt:
        log_notification("Program interrupted. (Ctrl-C)")
        traceback.print_exc()
        result = 1
    except SystemExit:
        result = 1

    if is_windows():
        stop_parent_process_monitoring()

    t1 = time.time()
    log_notification("Command took %f seconds." % (t1 - t0,))

    return result

if __name__ == "__main__":
    return_code = main()
    sys.exit(return_code)

