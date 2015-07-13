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

    # Some Windows tools don’t like “duplicate” environment variables, i.e.
    # when only the case differs; we remove any lowercase version we find.
    # The loop is O(n²) but we don’t have that many entries so it’s all right.
    env_vars = [x.lower() for x in os.environ.keys()]
    for dupe in set([x for x in env_vars if env_vars.count(x) > 1]):
        del os.environ[dupe]

    result = 0
    try:
        module_instances = get_dependency_sorted_instances(modules, Module)

        if(module_instances is None):
            log_error(log_prefix() + "Unable to satisfy modules dependencies.")
            return 1

        env = Environment()
        setattr(env, 'modules', module_instances)

        for module_it in module_instances:
            if not module_it.load(env):
                result = -1
                break

    except KeyboardInterrupt:
        log_notification(log_prefix() + "Interrompu. Zy av, t'es un ouf toi")
        return 1
    except SystemExit:
        return 1

    return result

if(__name__ == "__main__"):
    return_code = main()
    sys.exit(return_code)

