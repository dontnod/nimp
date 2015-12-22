# -*- coding: utf-8 -*-

import platform

# Return True if the runtime platform is Windows, including MSYS
def is_windows():
    return is_msys() or platform.system() == 'Windows'


# Return True if the runtime platform is MSYS
def is_msys():
    return platform.system()[0:7] == 'MSYS_NT'

