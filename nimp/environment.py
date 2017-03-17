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
''' Class and function relative to the nimp environment, i.e. configuration
values and command line parameters set for this nimp execution '''

import argparse
import inspect
import logging
import os
import sys
import time

import nimp.command
import nimp.summary
import nimp.unreal

_LOG_FORMATS = {
    'standard': '%(asctime)s [%(levelname)s] %(message)s'
}

_SUMMARY_HANDLERS = {
    'default': nimp.summary.DefaultSummaryHandler,
    'unreal': nimp.unreal.UnrealSummaryHandler
}


class Environment:
    ''' Environment '''
    config_loaders = []
    argument_loaders = []

    def __init__(self):
        self.command = None
        self.root_dir = '.'
        self.environment = {}
        self.dry_run = False
        self.summary = None

    def load_argument_parser(self):
        ''' Returns an argument parser for nimp and his subcommands '''
        # Import project-local commands from .nimp/commands
        cmd_dict = _get_instances(nimp.commands, nimp.command.Command)
        command_list = list(cmd_dict.values())
        localpath = os.path.abspath(os.path.join(self.root_dir, '.nimp'))
        if localpath not in sys.path:
            sys.path.append(localpath)
        try:
            #pylint: disable=import-error
            import commands
            cmd_dict = _get_instances(commands, nimp.command.Command)
            command_list += list(cmd_dict.values())
        except ImportError:
            pass

        command_list = sorted(command_list,
                              key = lambda command: command.__class__.__name__)
        command_list = [it for it in command_list if not it.__class__.__name__.startswith('_')]

        prog_description = 'Script utilities to ship games, mostly Unreal Engine based ones.'
        parser = argparse.ArgumentParser(description = prog_description)
        log_group = parser.add_argument_group("Logging")

        log_group.add_argument('-s',
                               '--summary',
                               metavar='<file>',
                               help='Enables summary mode (c.f. documentation)',
                               type=str,
                               default=None)

        assert 'default' in _SUMMARY_HANDLERS
        log_group.add_argument('--summary-format',
                               metavar='<format>',
                               help='Choose the summary format',
                               type=str,
                               choices = list(_SUMMARY_HANDLERS.keys()),
                               default='default')


        log_group.add_argument('--do-nothing',
                               help='Just parses arguments and exits (used for CIS tests)',
                               action='store_true')

        log_group.add_argument('-v',
                               '--verbose',
                               help='Enable verbose mode',
                               default=False,
                               action="store_true")

        nimp.command.add_commands_subparser(command_list, parser, self)

        return parser

    def load_arguments(self):
        ''' Executes arguments loader to clean and tweak argument variables '''
        for argument_loader in Environment.argument_loaders:
            if not argument_loader(self):
                return False

        return True

    def run(self, argv):
        ''' Runs nimp with argv and argc '''
        exit_success = 0
        exit_error = 1
        exit_warnings = 2

        if not self._load_nimp_conf():
            return exit_error

        for config_loader in Environment.config_loaders:
            if not config_loader(self):
                logging.error('Error while loading nimp config')
                return exit_error

        # Loads argument parser, parses argv with it and adds command line para
        # meters as properties of the environment
        parser = self.load_argument_parser()
        arguments = parser.parse_args(argv[1:])
        for key, value in vars(arguments).items():
            setattr(self, key, value)

        summary_format = getattr(self, 'summary_format')
        with _SUMMARY_HANDLERS[summary_format](self) as log_handler:
            if hasattr(self, 'environment'):
                for key, val in self.environment.items():
                    os.environ[key] = val

            if self.command is None:
                logging.error("No command specified. Please try nimp -h to get a list of available commands")
                return exit_error

            if not self.load_arguments():
                logging.error('Error while loading environment parameters')
                return exit_error

            success = self.command.run(self) if not getattr(self, 'do_nothing') else True

            if not success:
                return exit_error

            # If command succeed and summary mode is on, we check for captured
            # errors or warnings
            if self.summary is not None:

                if log_handler.has_errors():
                    logging.error('Command succeeded with errors')
                    return exit_warnings

                if log_handler.has_warnings():
                    logging.warning('Command succeeded with warnings')
                    return exit_warnings

            return exit_success

    def format(self, fmt, **override_kwargs):
        ''' Interpolates given string with config values & command line para-
            meters set in the environment '''
        assert isinstance(fmt, str)
        kwargs = vars(self).copy()
        kwargs.update(override_kwargs)
        result = fmt.format(**kwargs)
        result = time.strftime(result)
        return result

    def call(self, method, *args, **override_kwargs):
        ''' Calls a method after interpolating its arguments '''
        kwargs = vars(self).copy()
        kwargs.update(override_kwargs)
        return method(*args, **kwargs)

    def check_config(self, *var_names):
        ''' Checks all configuration values are set in nimp configuration '''
        all_ok = True
        for it in var_names:
            if not hasattr(self, it):
                logging.error('Required configuration value "%s" was not found.')
                all_ok = False
        if not all_ok:
            logging.error('Check your .nimp.conf for missing configuration values')
        return all_ok

    def load_config_file(self, filename):
        ''' Loads a config file and adds its values to this environment '''
        settings_content = read_config_file(filename)

        if settings_content is None:
            return False

        for key, value in settings_content.items():
            setattr(self, key, value)

        return True

    def setup_envvars(self):
        ''' Applies environment variables from .nimp.conf '''

    def _load_nimp_conf(self):
        nimp_conf_dir = "."
        nimp_conf_file = ".nimp.conf"
        while os.path.abspath(os.sep) != os.path.abspath(nimp_conf_dir):
            if os.path.exists(os.path.join(nimp_conf_dir, nimp_conf_file)):
                break
            nimp_conf_dir = os.path.join("..", nimp_conf_dir)

        self.root_dir = nimp_conf_dir

        if not os.path.isfile(os.path.join(nimp_conf_dir, nimp_conf_file)):
            return True

        if not self.load_config_file(os.path.join(nimp_conf_dir, nimp_conf_file)):
            logging.error("Error loading %s", nimp_conf_file)
            return False

        return True

def execute_hook(hook_name, *args):
    ''' Executes a hook in the .nimp/hooks directory '''
    logging.debug('Looking for %s hook in .nimp/hooks', hook_name)
    hook_module = nimp.system.try_import('hooks.' + hook_name)
    if hook_module is None:
        return
    if not hasattr(hook_module, 'run'):
        logging.debug('No "run" method found in .nimp/hooks/%s module', hook_name)
        return

    return getattr(hook_module, 'run')(*args)

def read_config_file(filename):
    ''' Reads a config file and returns a dictionary with values defined in it '''
    try:
        conf = open(filename, "rb").read()
    except IOError as ex:
        logging.error("Unable to open configuration file: %s", ex)
        return None
    # Parse configuration file
    try:
        local_vars = {}
        #pylint: disable=exec-used
        exec(compile(conf, filename, 'exec'), None, local_vars)
        if "config" in local_vars:
            return local_vars["config"]
        logging.error("Configuration file %s has no 'config' section.", filename)
    #pylint: disable=broad-except
    except Exception as ex:
        logging.error("Unable to load configuration file %s: %s", filename, str(ex))
        return None

    return {}

def _get_instances(module, instance_type):
    result = {}
    module_dict = module.__dict__
    if "__all__" in module_dict:
        module_name = module_dict["__name__"]
        sub_modules_names = module_dict["__all__"]
        for sub_module_name_it in sub_modules_names:
            sub_module_complete_name = module_name + "." + sub_module_name_it
            try:
                sub_module_it = __import__(sub_module_complete_name, fromlist = ["*"])
            except ImportError as ex:
                logging.warning('Error importing local command %s: %s', sub_module_complete_name, ex)
                continue
            sub_instances = _get_instances(sub_module_it, instance_type)
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
