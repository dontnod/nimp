# -*- coding: utf-8 -*-
# Copyright (c) 2014-2019 Dontnod Entertainment

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

'''Class and function relative to the nimp environment, i.e. configuration
values and command line parameters set for this nimp execution'''

import argparse
import logging
import os
import re
import sys
import time

import nimp.command
import nimp.summary
import nimp.sys.platform
import nimp.system
import nimp.unreal
import nimp.utils.profiling
from nimp.exceptions import NimpCommandFailed
from nimp.utils.python import iter_plugins_entry_points

_LOG_FORMATS = {  # pylint: disable = invalid-name
    'standard': '%(asctime)s [%(levelname)s] %(message)s'
}

_SUMMARY_HANDLERS = {  # pylint: disable = invalid-name
    'default': nimp.summary.DefaultSummaryHandler,
    'unreal': nimp.unreal.UnrealSummaryHandler,
}


class Environment:
    '''Environment'''

    config_loaders = []
    argument_loaders = []

    def __init__(self):
        self.command = None
        self.command_list = []
        self.environment = {}
        self.dry_run = False
        self.summary = None
        self.debug_env = {}

    def load_argument_parser(self, parent_parser):
        '''Returns an argument parser for nimp and its subcommands'''
        # prog_description = 'Script utilities to ship games, mostly Unreal Engine based ones.'
        # parser = argparse.ArgumentParser(description = prog_description)
        prog_description = 'Script utilities to ship games, mostly Unreal Engine based ones.'
        parser = argparse.ArgumentParser(description=prog_description, parents=[parent_parser])
        log_group = parser.add_argument_group("Logging")
        profiling_group = parser.add_argument_group("Profiling")

        log_group.add_argument(
            '-s',
            '--summary',
            metavar='<file>',
            help='Enables summary mode (c.f. documentation)',
            type=str,
            default=None,
        )

        assert 'default' in _SUMMARY_HANDLERS
        log_group.add_argument(
            '--summary-format',
            metavar='<format>',
            help='Choose the summary format',
            type=str,
            choices=list(_SUMMARY_HANDLERS.keys()),
            default='default',
        )

        log_group.add_argument(
            '--do-nothing', help='Just parses arguments and exits (used for CIS tests)', action='store_true'
        )

        log_group.add_argument('-v', '--verbose', help='Enable verbose mode', action='store_true')

        profiling_group.add_argument('--nimp-profiling', help='Profile nimp command', action='store_true')

        nimp.command.add_commands_subparser(self.command_list, parser, self)

        return parser

    def load_arguments(self):
        '''Executes arguments loader to clean and tweak argument variables'''
        for argument_loader in Environment.argument_loaders:
            if not argument_loader(self):
                return False

        return True

    def set_parser_defaults(self, parser):
        # Reset `required` attribute when provided from config file
        for action in parser._actions:
            if action.dest in self.__dict__:
                default_value = self.__dict__.get(action.dest, None)
                if default_value is not None:
                    action.required = False
                    action.default = default_value

    def run(self, argv):
        '''Runs nimp with argv and argc'''
        exit_success = 0
        exit_error = 1
        exit_warnings = 2

        # parses sys.argv in search of a manual uproject input
        parent_parser = argparse.ArgumentParser(add_help=False)
        parent_parser.add_argument(
            '--uproject',
            metavar='<unreal project>',
            help='Select an Unreal project to work with, i.e. PRO/PRO.uproject',
            type=str,
        )
        parent_parser.add_argument(
            '--branch', metavar='<project branch>', help='Select a project branch to work with', type=str
        )
        parent_parser.add_argument(
            '--user-config', metavar='<config file>', help='Custom nimp configuration file', type=str
        )
        parent_parser.add_argument(
            '--default-to-config',
            action='store_true',
            default=False,
            help='If enabled, missing arguments will be read from the configuration files',
        )
        parent_args, unkown_args = parent_parser.parse_known_args(sys.argv[1:])

        # Set this early so we can use it from command.add_commands_subparser
        self.default_to_config = parent_args.default_to_config

        # verify that uproject seems somewhat legit
        self.validate_uproject(parent_args.uproject)

        # base_conf for monorepo
        if not self._load_nimp_conf('.baseNimp.conf'):
            return exit_error
        # legacy conf
        if not hasattr(self, 'root_dir') or not self.root_dir:
            if not self._load_nimp_conf('.nimp.conf'):
                return exit_error

        if parent_args.user_config:
            if not self._load_nimp_conf(parent_args.user_config):
                return exit_error

        for config_loader in Environment.config_loaders:
            if not config_loader(self):
                logging.error('Error while loading nimp config')
                return exit_error

        if not self._load_project_conf():
            return exit_error

        if not hasattr(self, 'root_dir') or not self.root_dir:
            self.root_dir = '.'

        # Discover platforms
        nimp.sys.platform.discover(self)

        # Discover all available commands
        nimp.command.discover(self)

        # Loads argument parser, parses argv with it and adds command line parameters
        # as properties of the environment
        parser = self.load_argument_parser(parent_parser)
        if self.default_to_config:
            self.set_parser_defaults(parser)
        arguments, unknown = parser.parse_known_args(argv[1:])

        # TODO: remove this crappy hacks
        arguments.branch = self.branch if hasattr(self, 'branch') and arguments.branch is None else arguments.branch
        arguments.uproject = self.uproject if hasattr(self, 'uproject') else arguments.uproject
        self.parser = arguments
        for key, value in vars(arguments).items():
            setattr(self, key, value)

        # Exit if any problem with SliceJobIndex and SliceJobCount
        if self.has_attribute('slice_job_index') != self.has_attribute('slice_job_count'):
            parser.exit(1, '[ERROR] SliceJobIndex and SliceJobCount need to be used together\n')
        if self.has_attribute('slice_job_index') and self.has_attribute('slice_job_count'):
            if self.slice_job_index > self.slice_job_count:
                parser.exit(1, '[ERROR] SliceJobIndex should be inferior to SliceJobCount\n')

        # Exit if any unknown argument
        if unknown and any(unknown):
            parser.print_usage(sys.stderr)
            parser.exit(1, '%s: error: unrecognized arguments: %s\n' % (parser.prog, ' '.join(unknown)))

        summary_format = getattr(self, 'summary_format')
        with _SUMMARY_HANDLERS[summary_format](self) as log_handler:
            if "NIMP_LOG_FILE" in os.environ:
                # PATCHING ROOT LOGGER
                logging.getLogger().addHandler(log_handler.log_all_handler)

            # Always display engine and selected uproject info
            self.display_unreal_info()

            if hasattr(self, 'environment'):
                for key, val in self.environment.items():
                    try:  # TODO: should we throw?
                        os.environ[key] = self.format(val)
                    except KeyError:
                        os.environ[key] = val
                        logging.warning(
                            "Could not interpolate %s. Adding un-interpolated %s=%s to environment",
                            val,
                            key,
                            val,
                        )

            if self.command is None:
                logging.error("No command specified. Please try nimp -h to get a list of available commands")
                return exit_error

            if not self.load_arguments():
                logging.error('Error while loading environment parameters')
                return exit_error

            success = False
            if getattr(self, 'do_nothing'):
                success = True
            else:
                try:
                    with nimp.utils.profiling.nimp_profile(self):
                        success = self.command.run(self)
                        if not success:
                            raise NimpCommandFailed("Nimp command failed.")
                # pylint: disable=broad-except
                except NimpCommandFailed:
                    pass
                except Exception as exception:
                    logging.exception(exception)

            if not success:
                logging.error('Command failed')
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
        '''Interpolates given string with config values & command line para-
        meters set in the environment'''
        assert isinstance(fmt, str)
        kwargs = vars(self).copy()
        kwargs.update(override_kwargs)
        result = fmt.format(**kwargs)
        result = time.strftime(result)
        return result

    def call(self, method, *args, **override_kwargs):
        '''Calls a method after interpolating its arguments'''
        kwargs = vars(self).copy()
        kwargs.update(override_kwargs)
        return method(*args, **kwargs)

    def check_config(self, *var_names):
        '''Checks all configuration values are set in nimp configuration'''
        all_ok = True
        for it in var_names:
            if not hasattr(self, it):
                logging.error('Required configuration value "%s" was not found.', it)
                all_ok = False
        if not all_ok:
            logging.error('Check your .nimp.conf for missing configuration values')
        return all_ok

    def load_config_file(self, filename):
        '''Loads a config file and adds its values to this environment'''
        settings_content = read_config_file(filename)

        if settings_content is None:
            return False

        for key, value in settings_content.items():
            setattr(self, key, value)
            self.debug_env.update({key: value})

        return True

    def setup_envvars(self):
        '''Applies environment variables from .nimp.conf'''

    def _load_nimp_conf(self, conf_file):
        '''legacy - loads project conf before pg8 4.24 preiew - xpj_conf in the future ?'''
        nimp_conf_file = conf_file
        nimp_conf_dir = nimp.system.find_dir_containing_file(nimp_conf_file)

        if not nimp_conf_dir:
            logging.debug('No xpj conf it seems.')
            return True

        if not self.load_config_file(os.path.join(nimp_conf_dir, nimp_conf_file)):
            logging.error('Error loading %s', nimp_conf_file)
            return False

        self.root_dir = nimp_conf_dir

        return True

    def _load_project_conf(self):
        '''Loads project conf inside uproject folder - leaves ability to have xpj conf in xpj folder'''
        if not hasattr(self, 'uproject_dir') or not self.uproject_dir:
            return True
        if not hasattr(self, 'unreal_dir') or not self.unreal_dir:
            return True

        nimp_conf_file = '.nimp.conf'

        if not os.path.isfile(os.path.join(self.uproject_dir, nimp_conf_file)):
            return True

        if not self.load_config_file(os.path.join(self.uproject_dir, nimp_conf_file)):
            logging.error('Error loading project conf : %s', nimp_conf_file)
            return False

        # Assume Unreal dir is at root
        # TODO: This is a clumsy way to find root, find another way.
        unreal_file = os.path.join(self.unreal_root_path, 'Engine', 'Build', 'Build.version')
        root_dir = nimp.system.find_dir_containing_file(unreal_file)

        if not root_dir:
            logging.error('%s not found. It is now a nimp requirement.' % unreal_file)
            return False
        self.root_dir = root_dir

        logging.debug('nimp_file %s', os.path.join(self.uproject_dir, nimp_conf_file))

        # this can override settings from .nimp.conf
        additionnal_conf_file = os.path.join(self.uproject_dir, '.nimp', 'config.py')
        if os.path.exists(additionnal_conf_file):
            if not self.load_config_file(os.path.join(additionnal_conf_file)):
                logging.error('Error loading project conf : %s', additionnal_conf_file)
                return False

        return True

    def validate_uproject(self, urpoject):
        if not urpoject:
            return

        self._uproject = urpoject
        # valid --uproject param would be like NWD/NWD.uproject
        search_pattern = re.compile(r'^[\\|/]?(?P<uproject>[\w][\w][\w])[\\|/](?P=uproject).uproject$', re.IGNORECASE)
        if re.search(search_pattern, self._uproject):
            self._uproject_path = os.path.normpath(self._uproject)
            self._uproject = re.findall(search_pattern, self._uproject_path)[0].upper()
        # TODO: we could try and auto-detect branch based off vcs feedback - especially for buildbot
        logging.debug('uproject specified by user : %s' % self._uproject)

    def display_unreal_info(self):
        '''display engine and selected uproject info'''
        if hasattr(self, 'unreal_full_version') and hasattr(self, 'unreal_dir'):
            logging.info(f'Found Unreal engine {self.unreal_full_version} in {self.unreal_dir}')
        else:
            logging.info('No Unreal engine loaded')
        if hasattr(self, 'uproject') and hasattr(self, 'uproject_dir'):
            logging.info(f'Found Unreal project {self.uproject} in {self.uproject_dir}')
        else:
            logging.info('No Unreal project loaded')

    def has_attribute(self, attribute_name):
        '''Check that the attribute exists and has a value'''
        return hasattr(self, attribute_name) and getattr(self, attribute_name) is not None


def execute_hook(hook_name, *args):
    '''Executes a hook in the .nimp/hooks directory'''
    # Always look for project level hook first
    hook_module = nimp.system.try_import('hooks.' + hook_name)
    if hook_module is None:  # If none found, try plugins level
        for entry in iter_plugins_entry_points():
            hook_module = nimp.system.try_import(entry.module + '.hooks.' + hook_name)
            if hook_module:
                break
    if hook_module is None:
        return True
    logging.info('Found %s hook', hook_name)
    return hook_module.run(*args)


def read_config_file(filename):
    '''Reads a config file and returns a dictionary with values defined in it'''
    try:
        conf = open(filename, "rb").read()
    except IOError as ex:
        logging.error("Unable to open configuration file: %s", ex)
        return None
    # Parse configuration file
    try:
        local_vars = {}
        # pylint: disable=exec-used
        exec(compile(conf, filename, 'exec'), local_vars)
        if "config" in local_vars:
            return local_vars["config"]
        logging.error("Configuration file %s has no 'config' section.", filename)
    # pylint: disable=broad-except
    except Exception as ex:
        logging.error("Unable to load configuration file %s: %s", filename, str(ex))
        return None

    return {}
