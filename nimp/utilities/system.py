# -*- coding: utf-8 -*-

import platform

#-------------------------------------------------------------------------------
# Return True if the runtime platform is MSYS
def is_msys():
    return platform.system()[0:7] == 'MSYS_NT'

