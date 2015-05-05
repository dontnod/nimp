# -*- coding: utf-8 -*-

from nimp.utilities.logging import *

#-------------------------------------------------------------------------------
class Module:
    #---------------------------------------------------------------------------
    def __init__(self, name, dependencies):
        self._name = name
        self._dependencies = dependencies

    #---------------------------------------------------------------------------
    def name(self):
        return self._name

    #---------------------------------------------------------------------------
    def dependencies(self):
        return self._dependencies

    #---------------------------------------------------------------------------
    def load(self, env):
        assert(False)

#-------------------------------------------------------------------------------
def run_module(module_class, chgr_configuration, additional_arguments = []):
    module = module_class()
    parser = argparse.ArgumentParser()

    module.configure_arguments(parser)
    parser.set_defaults(**chgr_configuration.__dict__)

    (module_arguments, unknown_args) = parser.parse_known_args(chgr_configuration.unknown_args + additional_arguments)
    module_arguments_dictionary      = module_arguments.__dict__
    for key in module_arguments_dictionary:
        setattr(chgr_configuration, key, module_arguments_dictionary[key])

    setattr(chgr_configuration, "unknown_args", unknown_args)
    return module.run(chgr_configuration)
