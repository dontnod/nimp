#!/usr/bin/env python
# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import sys
sys.dont_write_bytecode = 1

import inspect
import time

from nimp import modules
from nimp.modules.module import *
from nimp.utilities.inspection import *
from nimp.utilities.environment import *

#-------------------------------------------------------------------------------
def main():
    result = 0
    try:
        module_instances = get_dependency_sorted_instances(modules, Module)

        if(module_instances is None):
            log_error("[nimp] Unable to satisfy modules dependencies.")
            return 1

        env = Environment()
        setattr(env, 'modules', module_instances)

        for module_it in module_instances:
            if not module_it.load(env):
                result = -1
                break

    except KeyboardInterrupt:
        log_notification("[nimp] Interrompu. Zy av, t'es un ouf toi")
        return 1
    except SystemExit:
        return 1

    return result

if(__name__ == "__main__"):
    return_code = main()
    sys.exit(return_code)
