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
''' Abstract class for commands '''

import abc
import argparse

class Command(metaclass=abc.ABCMeta):
    ''' Abstract class for commands '''

    def __init__(self):
        pass

    @abc.abstractmethod
    def configure_arguments(self, env, parser):
        ''' Registers arguments definition in command parser '''
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
                                nargs   = argparse.REMAINDER,
                                default = [])
        else:
            assert False, 'Unknown argument type'

def load_arguments(env):
    ''' Standardizes some environment parameters and sets new values '''
    if hasattr(env, 'free_parameters') and env.free_parameters is not None:
        for key, value in [ x.split('=') for x in env.args]:
            setattr(env, key, value)

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

    if hasattr(env, "platform") and env.platform is not None:
        if env.platform.lower() in std_platforms:
            env.platform =  std_platforms[env.platform.lower()]

        env.is_win32 = env.platform == "win32"
        env.is_win64 = env.platform == "win64"
        env.is_ps3   = env.platform == "ps3"
        env.is_ps4   = env.platform == "ps4"
        env.is_x360  = env.platform == "xbox360"
        env.is_xone  = env.platform == "xboxone"
        env.is_linux = env.platform == "linux"
        env.is_mac   = env.platform == "mac"

        env.is_microsoft_platform = env.is_win32 or env.is_win64 or env.is_x360 or env.is_xone
        env.is_sony_platform      = env.is_ps3 or env.is_ps4

    if hasattr(env, 'configuration') and env.configuration is not None:
        std_configs = { 'debug'    : 'debug',
                        'devel'    : 'devel',
                        'release'  : 'release',
                        'test'     : 'test',
                        'shipping' : 'shipping',
                      }

        if env.configuration.lower() in std_configs:
            env.configuration = std_configs[env.configuration.lower()]
        else:
            env.configuration = ""

    return True

