'''Helper functions for module handling'''

from __future__ import annotations

import inspect
import logging
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from importlib.metadata import EntryPoint
    from typing import Generator


def get_class_instances(module, instance_type, result, instance_args=[], instance_kwargs={}):
    module_dict = module.__dict__
    if '__all__' in module_dict:
        module_name = module_dict['__name__']
        sub_modules_names = module_dict['__all__']
        for sub_module_name_it in sub_modules_names:
            sub_module_complete_name = f'{module_name}.{sub_module_name_it}'
            try:
                sub_module_it = __import__(sub_module_complete_name, fromlist=['*'])
            except (ImportError, TabError) as ex:
                logging.warning('Error importing module %s: %s', sub_module_complete_name, ex)
                continue
            get_class_instances(
                sub_module_it, instance_type, result, instance_args=instance_args, instance_kwargs=instance_kwargs
            )

    module_attributes = dir(module)
    for attribute_name in module_attributes:
        attribute_value = getattr(module, attribute_name)
        is_valid = attribute_value != instance_type
        is_valid = is_valid and inspect.isclass(attribute_value)
        is_valid = is_valid and issubclass(attribute_value, instance_type)
        is_valid = is_valid and not inspect.isabstract(attribute_value)
        if is_valid:
            try:
                result[attribute_value.__name__] = attribute_value(*instance_args, **instance_kwargs)
            except Exception as ex:
                logging.warning('Error creating %s %s: %s', instance_type.__name__, attribute_value.__name__, ex)


def iter_plugins_entry_points() -> Generator[EntryPoint, None, None]:
    eps = entry_points()
    if hasattr(eps, "select"):
        yield from eps.select(group="nimp.plugins")
    elif hasattr(eps, "get"):
        yield from eps.get("nimp.plugins", [])
    else:
        raise NotImplementedError(f"unexpected value for importlib.metadata.entry_points ({type(eps)})")
