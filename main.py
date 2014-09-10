# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# imports
#-------------------------------------------------------------------------------
import sys
sys.dont_write_bytecode = 1
sys.path.append("../../third_parties/python")

import inspect
import modules
import time
import traceback

from    modules.module          import *

from    utilities.inspection    import *

#-------------------------------------------------------------------------------
# main
#-------------------------------------------------------------------------------
def main():
    result = 0
    try:
        module_instances = get_dependency_sorted_instances(modules, Module)

        if(module_instances is None):
            log_error("Unable to satisfy modules dependencies.")
            return 1

        class Context(object):
            pass

        context = Context()
        setattr(context, 'modules', module_instances)

        for module_it in module_instances:
            if not module_it.load(context):
                result = -1
                break

    except KeyboardInterrupt:
        log_notification("Interrompu. Zy av, t'es un ouf toi")
        return 1
    except SystemExit:
        return 1

    return result

if(__name__ == "__main__"):
    return_code = main()
    sys.exit(return_code)
