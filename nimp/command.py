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
''' Abstract class for commands '''

import abc
import logging
import re

class Command(metaclass=abc.ABCMeta):
    ''' Abstract class for commands '''

    def __init__(self):
        pass

    @abc.abstractmethod
    def configure_arguments(self, env, parser):
        ''' Registers arguments definition in command parser '''
        pass

    @abc.abstractmethod
    def is_available(self, env):
        ''' Returns a tuple (bool, disabled reason to know why a command is
            currently disabled '''
        pass

    @abc.abstractmethod
    def run(self, env):
        ''' Executes the command '''
        pass

def add_common_arguments(parser, *arg_ids):
    ''' Adds commonly used arguments to command line '''
    for arg_id in arg_ids:
        if arg_id == 'platform':
            parser.add_argument('-p', '--platform',
                                help = 'Platform',
                                metavar = '<platform>')
        elif arg_id == 'configuration':
            parser.add_argument('-c', '--configuration',
                                help = 'Configuration',
                                metavar = '<configuration>')
        elif arg_id == 'target':
            parser.add_argument('-t', '--target',
                                help = 'Target',
                                metavar = '<target>',
                                choices = ['game', 'editor', 'tools'])
        elif arg_id == 'revision':
            parser.add_argument('-r',
                                '--revision',
                                help = 'Revision',
                                metavar = '<revision>')

        elif arg_id == 'free_parameters':
            parser.add_argument('free_parameters',
                                help    = 'Add a key/value pair for use in string interpolation',
                                metavar = '<key>=<value>',
                                nargs   = '*',
                                default = [])
        else:
            assert False, 'Unknown argument type'

def load_arguments(env):
    ''' Standardizes some environment parameters and sets new values '''
    if hasattr(env, 'free_parameters') and env.free_parameters is not None:
        for key, value in [ x.split('=') for x in env.free_parameters]:
            setattr(env, key, value)

    if hasattr(env, "platform") and env.platform is not None:
        def sanitize_platform(platform):
            std_platforms = { "ps4"       : "ps4",
                              "orbis"     : "ps4",
                              "xboxone"   : "xboxone",
                              "dingo"     : "xboxone",
                              "win32"     : "win32",
                              "pcconsole" : "win32",
                              "win64"     : "win64",
                              "pc"        : "win64",
                              "windows"   : "win64",
                              "xbox360"   : "xbox360",
                              "x360"      : "xbox360",
                              "ps3"       : "ps3",
                              "linux"     : "linux",
                              "mac"       : "mac",
                              "macos"     : "mac" }

            if platform.lower() not in std_platforms:
                return platform
            return std_platforms[platform.lower()]

        env.platform = '+'.join(map(sanitize_platform, env.platform.split('+')))

        env.is_win32 = 'win32'   in env.platform.split('+')
        env.is_win64 = 'win64'   in env.platform.split('+')
        env.is_ps3   = 'ps3'     in env.platform.split('+')
        env.is_ps4   = 'ps4'     in env.platform.split('+')
        env.is_x360  = 'xbox360' in env.platform.split('+')
        env.is_xone  = 'xboxone' in env.platform.split('+')
        env.is_linux = 'linux'   in env.platform.split('+')
        env.is_mac   = 'mac'     in env.platform.split('+')

        env.is_microsoft_platform = env.is_win32 or env.is_win64 or env.is_x360 or env.is_xone
        env.is_sony_platform      = env.is_ps3 or env.is_ps4

    if hasattr(env, 'configuration') and env.configuration is not None:
        def sanitize_config(config):
            std_configs = { 'debug'    : 'debug',
                            'devel'    : 'devel',
                            'release'  : 'release',
                            'test'     : 'test',
                            'shipping' : 'shipping',
                          }

            if config.lower() not in std_configs:
                return ""
            return std_configs[config.lower()]

        env.configuration = '+'.join(map(sanitize_config, env.configuration.split('+')))

    return True

def add_commands_subparser(commands, parser, env):
    ''' Adds a list of commands to a subparser '''
    command_description = ('Commands marked with /!\\ are currently unavailable.'
                           ' You can issue "nimp <command> -h" to know why '
                           '<command> is currently disabled')
    subparsers  = parser.add_subparsers(metavar = '<command>',
                                        description = command_description )

    for command_it in commands:
        command_class = type(command_it)
        name_array = re.findall('[A-Z][^A-Z]*', command_class.__name__)
        command_name = '-'.join([it.lower() for it in name_array])

        enabled, reason = command_it.is_available(env)
        description = ''
        command_help = command_class.__doc__ or "NO HELP AVAILABLE, FIX ME!"
        command_help = command_help.split('\n')[0]

        if not enabled:
            description = 'This command is currently disabled :\n' + reason
            command_help = '/!\\ ' + command_help

        command_parser = subparsers.add_parser(command_name,
                                               description = description,
                                               help = command_help)
        command_it.configure_arguments(env, command_parser)

        command_to_run = command_it
        if not enabled:
            command_to_run = DisabledCommand(reason)
        command_parser.set_defaults(command = command_to_run)

class CommandGroup(Command):
    ''' Creates subparser from commands '''
    def __init__(self, sub_commands):
        super(CommandGroup, self).__init__()
        self._sub_commands = sub_commands

    def configure_arguments(self, env, parser):
        add_commands_subparser(self._sub_commands, parser, env)

    @abc.abstractmethod
    def is_available(self, env):
        assert False

    def run(self, env):
        assert False

class DisabledCommand(Command):
    ''' Command printing a help text to why it is currently disabled  '''
    def __init__(self, help_text):
        super(DisabledCommand, self).__init__()
        self._help = help_text

    def configure_arguments(self, env, parser):
        assert False

    def is_available(self, env):
        assert False

    def run(self, env):
        logging.error('This command is currently unavailable')
        logging.error(self._help)
