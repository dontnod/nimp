# -*- coding: utf-8 -*-

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

    return {}

