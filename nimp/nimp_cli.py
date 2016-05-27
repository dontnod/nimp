# -*- coding: utf-8 -*-
# Copyright (c) 2016 Dontnod Entertainment

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

import argparse
import inspect
import logging
import os
import platform
import sys
import time
import traceback

import nimp.commands.command
import nimp.utilities.environment
import nimp.utilities.system

if nimp.utilities.system.is_windows():
    import nimp.utilities.windows_utilities

sys.dont_write_bytecode = 1

_LOG_FORMATS = {
    'standard': '%(asctime)s [%(levelname)s] %(message)s'
}

if 'MSYS_NT' in platform.system():
    raise NotImplementedError('MSYS Python is not supported; please use MimGW Python instead')

def _load_config(env):
    nimp_conf_dir = "."
    nimp_conf_file = ".nimp.conf"
    while os.path.abspath(os.sep) != os.path.abspath(nimp_conf_dir):
        if os.path.exists(os.path.join(nimp_conf_dir, nimp_conf_file)):
            break
        nimp_conf_dir = os.path.join("..", nimp_conf_dir)

    env.root_dir = nimp_conf_dir

    if not os.path.isfile(os.path.join(nimp_conf_dir, nimp_conf_file)):
        return True

    if not env.load_config_file(os.path.join(nimp_conf_dir, nimp_conf_file)):
        logging.error("Error loading %s", nimp_conf_file)
        return False

    return True

def _get_instances(module, instance_type):
    result = _recursive_get_instances(module, instance_type)
    return list(result.values())

def _recursive_get_instances(module, instance_type):
    result = {}
    module_dict = module.__dict__
    if "__all__" in module_dict:
        module_name = module_dict["__name__"]
        sub_modules_names = module_dict["__all__"]
        for sub_module_name_it in sub_modules_names:
            sub_module_complete_name = module_name + "." + sub_module_name_it
            sub_module_it = __import__(sub_module_complete_name, fromlist = ["*"])
            sub_instances = _recursive_get_instances(sub_module_it, instance_type)
            for (klass, instance) in sub_instances.items():
                result[klass] = instance


    module_attributes = dir(module)
    for attribute_name in module_attributes:
        attribute_value = getattr(module, attribute_name)
        is_valid = attribute_value != instance_type
        is_valid = is_valid and inspect.isclass(attribute_value)
        is_valid = is_valid and (not hasattr(attribute_value, 'abstract') or not getattr(attribute_value, 'abstract'))
        is_valid = is_valid and issubclass(attribute_value, instance_type)
        if is_valid:
            result[attribute_value.__name__] = attribute_value()
    return result

def _load_commands(env):
    # Import project-local commands from .nimp/commands
    result = _get_instances(nimp.commands, nimp.commands.command.Command)
    localpath = os.path.abspath(os.path.join(env.root_dir, '.nimp'))
    if localpath not in sys.path:
        sys.path.append(localpath)
    try:
        #pylint: disable=import-error
        import commands
        result += _get_instances(commands, nimp.commands.command.Command)
    except ImportError:
        pass

    return result

def _load_arguments(env, commands):
    parser = argparse.ArgumentParser(formatter_class=argparse.HelpFormatter)
    log_group = parser.add_argument_group("Logging")

    log_group.add_argument('--log-format',
                           help='Set log format',
                           metavar = "FORMAT_NAME",
                           type=str,
                           default="standard",
                           choices   = _LOG_FORMATS)

    log_group.add_argument('-v',
                           '--verbose',
                           help='Enable verbose mode',
                           default=False,
                           action="store_true")

    subparsers  = parser.add_subparsers(title='Commands')
    for command_it in commands:
        command_parser = subparsers.add_parser(command_it.name,
                                               help = command_it.help)
        if not command_it.configure_arguments(env, command_parser):
            return False
        command_parser.set_defaults(command_to_run = command_it)

    arguments = parser.parse_args()
    for key, value in vars(arguments).items():
        setattr(env, key, value)

    env.setup_envvars()
    return True

def _init_logging(env):
    log_level = logging.DEBUG if env.verbose else logging.INFO
    logging.basicConfig(format=_LOG_FORMATS[env.log_format], level=log_level)

def main():
    ''' Nimp entry point '''
    start = time.time()

    result = 0
    try:
        if nimp.utilities.system.is_windows():
            nimp_monitor = nimp.utilities.windows_utilities.NimpMonitor()
            nimp_monitor.start()

        env = nimp.utilities.environment.Environment()
        if not  _load_config(env):
            return 1

        commands = _load_commands(env)

        if not _load_arguments(env, commands):
            return 1

        if env.command_to_run is None:
            logging.error("No command specified. Please try nimp -h to get a list of available commands")
            return 1

        _init_logging(env)

        env.command_to_run.sanitize(env)
        return env.command_to_run.run(env)

    except KeyboardInterrupt:
        logging.info("Program interrupted. (Ctrl-C)")
        traceback.print_exc()
        result = 1
    except SystemExit:
        result = 1

    if nimp.utilities.system.is_windows():
        nimp_monitor.stop()

    end = time.time()
    logging.info("Command took %f seconds.", end - start)

    return result

if __name__ == "__main__":
    sys.exit(main())

