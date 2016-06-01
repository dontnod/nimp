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
''' Class and function relative to the nimp environment, i.e. configuration
values and command line parameters set for this nimp execution '''

import logging
import os
import platform
import time

import nimp.system
import nimp.ue3
import nimp.ue4

class Environment:
    ''' Environment
    \todo Test Todo'''

    def __init__(self):
        # Some Windows tools don’t like “duplicate” environment variables, i.e.
        # where only the case differs; we remove any lowercase version we find.
        # The loop is O(n²) but we don’t have that many entries so it’s all right.
        env_vars = [x.lower() for x in os.environ.keys()]
        for dupe in set([x for x in env_vars if env_vars.count(x) > 1]):
            dupelist = sorted([x for x in os.environ.keys() if x.lower() == dupe ])
            logging.warning("Fixing duplicate environment variable: " + '/'.join(dupelist))
            for duplicated in dupelist[1:]:
                del os.environ[duplicated]
        # … But in some cases (Windows Python) the duplicate variables are masked
        # by the os.environ wrapper, so we do it another way to make sure there
        # are no dupes:
        for key in sorted(os.environ.keys()):
            val = os.environ[key]
            del os.environ[key]
            os.environ[key] = val

        self.command_to_run = None
        self.root_dir = None
        self.environment = {}

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

    def map_files(self):
        ''' Returns a file mapper to list / copy files. '''
        def _default_mapper(_, dest):
            yield (self.root_dir, dest)
        return nimp.system.FileMapper(_default_mapper, format_args = vars(self))

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
        if hasattr(self, 'environment'):
            for key, val in self.environment.items():
                os.environ[key] = val

    def execute_hook(self, hook_name):
        ''' Executes a hook in the .nimp/hooks directory '''
        pass

def read_config_file(filename):
    ''' Reads a config file and returns a dictionary with values defined in it '''
    try:
        conf = open(filename, "rb").read()
    except IOError as exception:
        logging.error("Unable to open configuration file : %s", exception)
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
        logging.error("Unable to load configuration file %s : %s", filename, str(ex))
        return None

    return {}

def sanitize_platform(env):
    ''' Standardizes platform names and sets helpers booleans '''
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

    if nimp.system.is_windows():
        env.platform = 'win64'
    elif platform.system() == 'Darwin':
        env.platform = 'mac'
    else:
        env.platform = 'linux'

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
