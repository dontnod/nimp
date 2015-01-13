# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# imports
#-------------------------------------------------------------------------------
import inspect
import os

from utilities.sorting import *

#-------------------------------------------------------------------------------
# get_local_module_dependencies
# -> Recursively resolves the import dependencies of a module
#-------------------------------------------------------------------------------
def get_local_module_dependencies(base_directory, module, modules_found = []):
    if modules_found is None:
        modules_found = []

    module_attributes = module.__dict__
    for (attribute_name, attribute_value) in module_attributes:
        dependency = None
        if inspect.ismodule(attribute_value):
            dependency = attribute_value
        else:
            dependency = inspect.getmodule(attribute_value)
        if dependent_module is not None and hasattr(dependent_module, "__file__"):
            module_path     = dependency.__file__
            relative_path   = os.path.relpath(module_path, base_directory)
            relative_path   = os.path.normpath(relative_path)
            if(     relative_path[0] != '.'
                and relative_path[1] != '.'
                and relative_path not in modules_found):
                modules_found = modules_found + [relative_path]
                get_local_module_dependencies(base_directory, dependency, modules_found)
    return modules_found

#-------------------------------------------------------------------------------
# get_instances
def get_instances(module, type):
    result = instanciate_types_suppress_doubles(module, type)
    return result.values()


#-------------------------------------------------------------------------------
# get_dependency_sorted_instances
def get_dependency_sorted_instances(module, type):
    result = instanciate_types_suppress_doubles(module, type)
    if result is None:
        return None

    result = topological_sort(result.values())
    return result

#-------------------------------------------------------------------------------
# get_dependency_sorted_instances_named
def get_dependency_sorted_instances_named(module, type, instances_names):
    result          = []
    all_instances   = get_instances(module, type)

    for instance_name_it in instances_names:
        instance = None

        for instance_it in all_instances:
            if instance_it.name() == instance_name_it:
                instance = instance_it
                break

        if instance is None:
            log_error("Can't find an instance of {0} named {1} in {2}.",
                      type,
                      instance_name_it,
                      module)
            return None

        sorted_dependencies = topological_sort_node(instance, all_instances)

        if sorted_dependencies is None:
            return None

        for dependency_it in sorted_dependencies:
            if not dependency_it in result:
                result.append(dependency_it)
        return result

#-------------------------------------------------------------------------------
# instanciate_types_suppress_doubles
def instanciate_types_suppress_doubles(module, type):
    result = {}
    module_dict = module.__dict__
    if "__all__" in module_dict:
        module_name         = module_dict["__name__"]
        sub_modules_names   = module_dict["__all__"]
        for sub_module_name_it in sub_modules_names:
            sub_module_complete_name = module_name + "." + sub_module_name_it
            sub_module_it            = __import__(sub_module_complete_name, fromlist = ["*"])
            sub_instances            = instanciate_types_suppress_doubles(sub_module_it, type)
            for (klass, instance) in sub_instances.items():
                result[klass] = instance


    module_attributes = dir(module)
    for attribute_name in  module_attributes:
        attribute_value = getattr(module, attribute_name)
        if attribute_value != type and inspect.isclass(attribute_value) and (not hasattr(attribute_value, 'abstract') or not getattr(attribute_value, 'abstract')) and issubclass(attribute_value, type):
            result[attribute_value.__name__] = attribute_value()
    return result
