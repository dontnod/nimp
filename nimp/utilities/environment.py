# -*- coding: utf-8 -*-
''' Class and function relative to the nimp environment, i.e. configuration
values and command line parameters set for this nimp execution '''

import time
import platform
import os

import nimp.utilities.file_mapper
import nimp.utilities.logging
import nimp.utilities.system
import nimp.utilities.ue3
import nimp.utilities.ue4

class Environment:
    ''' Environment '''

    def __init__(self):
        # Some Windows tools don’t like “duplicate” environment variables, i.e.
        # where only the case differs; we remove any lowercase version we find.
        # The loop is O(n²) but we don’t have that many entries so it’s all right.
        env_vars = [x.lower() for x in os.environ.keys()]
        for dupe in set([x for x in env_vars if env_vars.count(x) > 1]):
            dupelist = sorted([x for x in os.environ.keys() if x.lower() == dupe ])
            nimp.utilities.logging.log_warning("Fixing duplicate environment variable: " + '/'.join(dupelist))
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
        return nimp.utilities.file_mapper.FileMapper(_default_mapper, format_args = vars(self))

    def check_keys(self, *args):
        ''' Checks if a given key is set on this environment '''
        error_format = "{key} should be defined, either in settings or in command line arguments. Check those."
        return check_keys(vars(self), error_format, *args)

    #---------------------------------------------------------------------------
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


#---------------------------------------------------------------------------
def check_keys(dictionary, error_format, *args):
    ''' Checks a key is defined on environment '''
    result = True
    for in_key in args:
        if in_key not in dictionary:
            result = False
    return result

#---------------------------------------------------------------------------
def read_config_file(filename):
    try:
        conf = open(filename, "rb").read()
    except Exception as exception:
        log_error("Unable to open configuration file : {0}", exception)
        return None
    # Parse configuration file
    try:
        locals = {}
        exec(compile(conf, filename, 'exec'), None, locals)
        if "config" in locals:
            return locals["config"]
        log_error("Configuration file {0} has no 'config' section.", filename)
    except Exception as e:
        log_error("Unable to load configuration file {0}: {1}", filename, str(e))
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

    if nimp.utilities.system.is_windows():
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
