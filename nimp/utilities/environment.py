# -*- coding: utf-8 -*-

import time

from nimp.utilities.logging import *
from nimp.utilities.file_mapper import *

#-------------------------------------------------------------------------------
class Environment:
    #---------------------------------------------------------------------------
    def __init__(self):
        pass

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
        return FileMapper(format_args = vars(self))

    def check_keys(self, *args):
        error_format = "{key} should be defined, either in settings or in command line arguments. Check those."
        return check_keys(vars(self), error_format, *args)

    #---------------------------------------------------------------------------
    def load_config_file(self, filename):
        class Settings:
            pass

        settings = Settings()
        settings_content = _read_config_file(filename)

        if(settings_content is None):
            return False

        for key, value in settings_content.items():
            setattr(self, key, value)

        return True

    def standardize_names(self):
        if hasattr(self, "platform"):
            std_platforms = { "ps4"       : "PS4",
                              "orbis"     : "PS4",
                              "xboxone"   : "XboxOne",
                              "dingo"     : "XboxOne",
                              "win32"     : "Win32",
                              "pcconsole" : "Win32",
                              "win64"     : "Win64",
                              "pc"        : "Win64",
                              "windows"   : "Win64",
                              "xbox360"   : "XBox360",
                              "x360"      : "XBox360",
                              "ps3"       : "PS3" }

            if(self.platform.lower() in std_platforms):
                self.platform = std_platforms[self.platform.lower()]

            self.is_win32 = self.platform == "Win32"
            self.is_win64 = self.platform == "Win64"
            self.is_ps3   = self.platform == "PS3"
            self.is_ps4   = self.platform == "PS4"
            self.is_x360  = self.platform == "XBox360"
            self.is_xone  = self.platform == "XboxOne"

            self.is_microsoft_platform = self.is_win32 or self.is_win64 or self.is_x360 or self.is_xone
            self.is_sony_platform      = self.is_ps3 or self.is_ps4

            ue3_build_platforms = { "PS4"     : "ORBIS",
                                    "XboxOne" : "Dingo",
                                    "Win64"   : "Win64",
                                    "Win32"   : "Win32",
                                    "XBox360" : "Xbox360",
                                    "PS3"     : "PS3" }

            ue3_cook_platforms = { "PS4"     : "ORBIS",
                                   "XboxOne" : "Dingo",
                                   "Win64"   : "PC",
                                   "Win32"   : "PCConsole",
                                   "XBox360" : "Xbox360",
                                   "PS3"     : "PS3" }

            if(self.platform in ue3_cook_platforms):
                self.ue3_cook_platform = ue3_cook_platforms[self.platform]

            if(self.platform in ue3_build_platforms):
                self.ue3_build_platform = ue3_build_platforms[self.platform]

            ue4_build_platforms = { "PS4"     : "PS4",
                                    "XboxOne" : "XboxOne",
                                    "Win64"   : "Win64",
                                    "Win32"   : "Win32",
                                    "XBox360" : "Xbox360",
                                    "PS3"     : "PS3" }

            ue4_cook_platforms = { "PS4"     : "ORBIS",
                                   "XboxOne" : "XboxOne",
                                   "Win64"   : "PC",
                                   "Win32"   : "PCConsole",
                                   "XBox360" : "Xbox360",
                                   "PS3"     : "PS3" }

            if(self.platform in ue4_cook_platforms):
                self.ue4_cook_platform = ue4_cook_platforms[self.platform]
                configuration = self.configuration.lower() if hasattr(self, 'configuration') and self.configuration is not None else 'final'
                suffix = 'Final' if configuration in ['test', 'final'] else ''
                self.ue3_cook_directory = 'Cooked{0}{1}'.format(self.ue3_cook_platform, suffix)

            if(self.platform in ue4_build_platforms):
                self.ue4_build_platform = ue4_build_platforms[self.platform]

            upms_platforms = { "PS4"     : "PS4",
                               "XboxOne" : "XboxOne",
                               "Win64"   : "PC",
                               "Win32"   : "PCConsole",
                               "XBox360" : "Xbox360",
                               "PS3"     : "PS3" }

            if(self.platform in upms_platforms):
                self.upms_platform = upms_platforms[self.platform]

            if hasattr(self, 'dlc'):
                if self.dlc is None:
                    self.dlc = self.project

            dlc = self.dlc if hasattr(self, 'dlc') else self.project

            banks_platforms = { "Win32"   : "PC",
                                "Win64"   : "PC",
                                "XBox360" : "X360",
                                "XboxOne" : "XboxOne",
                                "PS3"     : "PS3",
                                "PS4"     : "PS4" }

            cmd_platforms = { "Win32"   : "Windows",
                              "Win64"   : "Windows",
                              "XBox360" : "XBox360",
                              "XboxOne" : "XboxOne",
                              "PS3"     : "PS3",
                              "PS4"     : "PS4" }

            if(self.platform in banks_platforms):
                self.wwise_banks_platform = banks_platforms[self.platform]
            if(self.platform in cmd_platforms):
                self.wwise_cmd_platform = cmd_platforms[self.platform]

#---------------------------------------------------------------------------
def check_keys(dict, error_format, *args):
    result = True
    for key in args:
        if not key in dict:
            log_error(log_prefix() + error_format, key = key)
            result = False
    return result

#---------------------------------------------------------------------------
def _read_config_file(filename):
    try:
        conf = open(filename, "rb").read()
    except Exception as exception:
        log_error(log_prefix() + "Unable to open configuration file : {0}", exception)
        return None
    # Parse configuration file
    try:
        locals = {}
        exec(compile(conf, filename, 'exec'), None, locals)
        if "config" in locals:
            return locals["config"]
        log_error(log_prefix() + "Configuration file {0} has no 'config' section.", filename)
    except Exception as e:
        log_error(log_prefix() + "Unable to load configuration file {0}: {1}", filename, str(e))
        return None

    return {}

