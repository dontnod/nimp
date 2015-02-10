# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
class Context:
    def __init__(self):
        pass

    def format(self, str, **override_kwargs):
        kwargs = vars(self)
        kwargs.update(override_kwargs)
        return str.format(**kwargs)

    def call(self, method, *args, **override_kwargs):
        kwargs = vars(self)
        kwargs.update(override_kwargs)
        return method(*args, **kwargs)
