# -*- coding: utf-8 -*-

from nimp.utilities.logging import *

#-------------------------------------------------------------------------------
class Context:
    def __init__(self):
        pass

    def format(self, str, **override_kwargs):
        kwargs = vars(self).copy()
        kwargs.update(override_kwargs)
        return str.format(**kwargs)

    def call(self, method, *args, **override_kwargs):
        kwargs = vars(self).copy()
        kwargs.update(override_kwargs)
        return method(*args, **kwargs)

    #---------------------------------------------------------------------------
    def load_config_file(self, filename):
        class Settings:
            pass

        settings         = Settings()
        settings_content = _read_config_file(filename)

        if(settings_content is None):
            return False

        for key, value in settings_content.items():
            setattr(self, key, value)

        return True

    def standardize_names(self):
        if hasattr(self, "platform"):
            std_platforms = {"ps4"       : "PS4",
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

            self.platform = std_platforms[self.platform.lower()]

            self.is_win32 = self.platform == "Win32"
            self.is_win64 = self.platform == "Win64"
            self.is_ps3   = self.platform == "PS3"
            self.is_ps4   = self.platform == "PS4"
            self.is_x360  = self.platform == "XBox360"
            self.is_xone  = self.platform == "XboxOne"

            self.is_microsoft_platform  = self.is_win32 or self.is_win64 or self.is_x360 or self.is_xone
            self.is_sony_platform       = self.is_ps3 or self.is_ps4

#---------------------------------------------------------------------------
def _read_config_file(filename):
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

