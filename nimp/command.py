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
                                # “Tiles” and “Lights” are a bit of a hack for now
                                choices = ['game', 'editor', 'tools', 'tiles', 'lights'])
        elif arg_id == 'revision':
            parser.add_argument('-r',
                                '--revision',
                                help = 'Revision',
                                metavar = '<revision>')

        elif arg_id == 'free_parameters':
            parser.add_argument('--free-parameters',
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

    return True

def add_commands_subparser(commands, parser, env):
    ''' Adds a list of commands to a subparser '''
    command_description = ('Commands marked with /!\\ are currently unavailable.'
                           ' You can issue "nimp <command> -h" to know why '
                           '<command> is currently disabled')
    subparsers = parser.add_subparsers(metavar = '<command>',
                                       description = command_description )

    for command_it in commands:
        command_class = type(command_it)
        name_array = re.findall('[A-Z][^A-Z]*', command_class.__name__)
        command_name = '-'.join([it.lower() for it in name_array])

        try:
            enabled, reason = command_it.is_available(env)
        except Exception as ex:
            enabled, reason = False, 'Unexpected error: ' + str(ex)

        description = ''
        command_help = command_class.__doc__ or "NO HELP AVAILABLE, FIX ME!"
        command_help = command_help.split('\n')[0]

        if not enabled:
            description = 'This command is currently disabled :\n' + reason
            command_help = '/!\\ ' + command_help

        command_parser = subparsers.add_parser(command_name,
                                               description = description,
                                               help = command_help)
        try:
            command_it.configure_arguments(env, command_parser)
        except Exception as ex:
            enabled, reason = False, 'Unexpected error: ' + str(ex)

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
