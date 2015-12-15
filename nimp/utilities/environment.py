# -*- coding: utf-8 -*-

import time
import platform

from nimp.utilities.logging import *
from nimp.utilities.file_mapper import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *
from nimp.utilities.perforce import *

#-------------------------------------------------------------------------------
class Environment:

    def __init__(self):
        # Some Windows tools don’t like “duplicate” environment variables, i.e.
        # where only the case differs; we remove any lowercase version we find.
        # The loop is O(n²) but we don’t have that many entries so it’s all right.
        env_vars = [x.lower() for x in os.environ.keys()]
        for dupe in set([x for x in env_vars if env_vars.count(x) > 1]):
            dupelist = sorted([x for x in os.environ.keys() if x.lower() == dupe ])
            log_warning("Fixing duplicate environment variable: " + '/'.join(dupelist))
            for d in dupelist[1:]:
                del os.environ[d]

    #---------------------------------------------------------------------------
    def format(self, str, **override_kwargs):
        kwargs = vars(self).copy()
        kwargs.update(override_kwargs)
        result = str.format(**kwargs)
        result = time.strftime(result)
        return result

    #---------------------------------------------------------------------------
    def call(self, method, *args, **override_kwargs):
        kwargs = vars(self).copy()
        kwargs.update(override_kwargs)
        return method(*args, **kwargs)

    #---------------------------------------------------------------------------
    def map_files(self):
        def default_mapper(src, dest):
            yield (self.root_dir, self.root_dir)
        return FileMapper(default_mapper, format_args = vars(self))

    def check_keys(self, *args):
        error_format = "{key} should be defined, either in settings or in command line arguments. Check those."
        return check_keys(vars(self), error_format, *args)

    #---------------------------------------------------------------------------
    def load_config_file(self, filename):
        class Settings:
            pass

        settings = Settings()
        settings_content = read_config_file(filename)

        if settings_content is None:
            return False

        for key, value in settings_content.items():
            setattr(self, key, value)

        return True


    def normalize_platform_string(self, platform):
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

        if platform.lower() in std_platforms:
            return std_platforms[platform.lower()]
        else:
            return ""


    #
    # Normalise configuration and platform names, then create some
    # convenient variables for various jobs
    #
    def standardize_names(self):
        # Detect Unreal Engine 3 or Unreal Engine 4

        self.is_ue3 = hasattr(self, 'project_type') and self.project_type is 'UE3'
        self.is_ue4 = hasattr(self, 'project_type') and self.project_type is 'UE4'

        # If none were provided, force a configuration and a platform name
        # using some sane project-specific defaults

        if not hasattr(self, 'configuration') or self.configuration == None:
            if self.is_ue4:
                self.configuration = 'devel'
            elif self.is_ue3:
                self.configuration = 'release'

        if not hasattr(self, 'platform') or self.platform == None:
            if self.is_ue4 or self.is_ue3:
                if is_msys():
                    self.platform = 'win64'
                elif platform.system() == 'Darwin':
                    self.platform = 'mac'
                else:
                    self.platform = 'linux'

        if not hasattr(self, 'target') or self.target == None:
            if self.is_ue4:
                if self.platform in ['win64', 'mac', 'linux']:
                    self.target = 'editor'
                else:
                    self.target = 'game'
            elif self.is_ue3:
                if self.platform == 'win64':
                    self.target = 'editor'
                else:
                    self.target = 'game'

        # Now properly normalise configuration and platform names

        if hasattr(self, 'configuration'):
            std_configs = { 'debug'    : 'debug',
                            'devel'    : 'devel',
                            'release'  : 'release',
                            'test'     : 'test',
                            'shipping' : 'shipping',
                          }

            if self.configuration.lower() in std_configs:
                self.configuration = std_configs[self.configuration.lower()]
            else:
                self.configuration = ""


        if hasattr(self, "platform"):
            self.platform = self.normalize_platform_string(self.platform)

            self.is_win32 = self.platform == "win32"
            self.is_win64 = self.platform == "win64"
            self.is_ps3   = self.platform == "ps3"
            self.is_ps4   = self.platform == "ps4"
            self.is_x360  = self.platform == "xbox360"
            self.is_xone  = self.platform == "xboxone"
            self.is_linux = self.platform == "linux"
            self.is_mac   = self.platform == "mac"

            self.is_microsoft_platform = self.is_win32 or self.is_win64 or self.is_x360 or self.is_xone
            self.is_sony_platform      = self.is_ps3 or self.is_ps4

            # UE3 stuff
            self.ue3_build_platform =  get_ue3_build_platform(self.platform)
            self.ue3_cook_platform =   get_ue3_cook_platform(self.platform)
            self.ue3_shader_platform = get_ue3_shader_platform(self.platform)

            if hasattr(self, "configuration"):
                self.ue3_build_configuration = get_ue3_build_config(self.configuration)
                self.ue4_build_configuration = get_ue4_build_config(self.configuration)

            cook_cfg = self.configuration if hasattr(self, 'configuration') else None
            cook_suffix = 'Final' if cook_cfg in ['test', 'shipping', None] else ''
            self.ue3_cook_directory = 'Cooked{0}{1}'.format(self.ue3_cook_platform, cook_suffix)

            # UE4 stuff
            self.ue4_build_platform = get_ue4_build_platform(self.platform)
            self.ue4_cook_platform  = get_ue4_cook_platform(self.platform)

            # Other stuff
            upms_platforms = { "ps4"     : "PS4",
                               "xboxone" : "XboxOne",
                               "win64"   : "PC",
                               "win32"   : "PCConsole",
                               "xbox360" : "Xbox360",
                               "ps3"     : "PS3" }

            if self.platform in upms_platforms:
                self.upms_platform = upms_platforms[self.platform]

            if hasattr(self, 'dlc'):
                if self.dlc is None:
                    self.dlc = 'main'

            dlc = self.dlc if hasattr(self, 'dlc') else 'main'
            if self.is_ue3:
                banks_platforms = { "win32"   : "PC",
                                    "win64"   : "PC",
                                    "xbox360" : "X360",
                                    "xboxone" : "XboxOne",
                                    "ps3"     : "PS3",
                                    "ps4"     : "PS4" }
            else:
                banks_platforms = { "win32"   : "Windows",
                                    "win64"   : "Windows",
                                    "xbox360" : "X360",
                                    "xboxone" : "XboxOne",
                                    "ps3"     : "PS3",
                                    "ps4"     : "PS4" }

            if self.platform in banks_platforms:
                self.wwise_banks_platform = banks_platforms[self.platform]


    #
    # Apply environment variables from .nimp.conf
    #
    def setup_envvars(self):
        if hasattr(self, 'environment'):
            for key, val in self.environment.items():
                os.environ[key] = val


#---------------------------------------------------------------------------
def check_keys(dict, error_format, *args):
    result = True
    for key in args:
        if not key in dict:
            log_error(error_format, key = key)
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

