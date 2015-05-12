# -*- coding: utf-8 -*-

from nimp.utilities.logging import *

#-------------------------------------------------------------------------------
class Module:
    #---------------------------------------------------------------------------
    def __init__(self, name, dependencies):
        self._name = name
        self._dependencies = dependencies

    #---------------------------------------------------------------------------
    def name(self):
        return self._name

    #---------------------------------------------------------------------------
    def dependencies(self):
        return self._dependencies

    #---------------------------------------------------------------------------
    def load(self, env):
        assert(False)

