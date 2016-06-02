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
import re
import sys
import time
import traceback

import nimp.command
import nimp.commands
import nimp.environment
import nimp.system

if nimp.system.is_windows():
    import nimp.windows

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
        is_valid = is_valid and issubclass(attribute_value, instance_type)
        is_valid = is_valid and not inspect.isabstract(attribute_value)
        if is_valid:
            result[attribute_value.__name__] = attribute_value()
    return result

def _load_commands(env):
    # Import project-local commands from .nimp/commands
    result = _get_instances(nimp.commands, nimp.command.Command)
    localpath = os.path.abspath(os.path.join(env.root_dir, '.nimp'))
    if localpath not in sys.path:
        sys.path.append(localpath)
    try:
        #pylint: disable=import-error
        import commands
        result += _get_instances(commands, nimp.command.Command)
    except ImportError:
        pass

    return sorted(result, key = lambda command: command.__class__.__name__)

def _load_parser(env, commands):
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
        command_class = type(command_it)
        name_array = re.findall('[A-Z][^A-Z]*', command_class.__name__)
        command_name = '-'.join([it.lower() for it in name_array])
        command_parser = subparsers.add_parser(command_name,
                                               help = command_class.__doc__)
        if not command_it.configure_arguments(env, command_parser):
            return False
        command_parser.set_defaults(command_to_run = command_it)

    return parser

def _load_arguments(env, commands):
    parser = _load_parser(env, commands)
    arguments = parser.parse_args()
    for key, value in vars(arguments).items():
        setattr(env, key, value)

    env.setup_envvars()
    return True

def _get_parser():
    env = nimp.environment.Environment()
    _load_config(env)
    commands = _load_commands(env)
    return _load_parser(env, commands)

def _init_logging(env):
    log_level = logging.DEBUG if env.verbose else logging.INFO
    logging.basicConfig(format=_LOG_FORMATS[env.log_format], level=log_level)

def main():
    ''' Nimp entry point '''
    start = time.time()

    result = 0
    try:
        if nimp.system.is_windows():
            nimp_monitor = nimp.windows.NimpMonitor()
            nimp_monitor.start()

        env = nimp.environment.Environment()
        if not  _load_config(env):
            return 1

        commands = _load_commands(env)

        if not _load_arguments(env, commands):
            return 1

        if env.command_to_run is None:
            logging.error("No command specified. Please try nimp -h to get a list of available commands")
            return 1

        _init_logging(env)

        if not env.command_to_run.sanitize(env):
            return 1

        return env.command_to_run.run(env)

    except KeyboardInterrupt:
        logging.info("Program interrupted. (Ctrl-C)")
        traceback.print_exc()
        result = 1
    except SystemExit:
        result = 1

    if nimp.system.is_windows():
        nimp_monitor.stop()

    end = time.time()
    logging.info("Command took %f seconds.", end - start)

    return result

if __name__ == "__main__":
    sys.exit(main())

