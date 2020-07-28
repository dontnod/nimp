
''' Platform-related configuration utilities '''

import platform

class Platform(object):
    def __init__(self):
        pass


def is_windows():
    ''' Return True if the runtime platform is Windows, including MSYS '''
    return is_msys() or platform.system() == 'Windows'

def is_msys():
    ''' Returns True if the platform is msys. '''
    return platform.system()[0:7] == 'MSYS_NT'

def is_osx():
    ''' Returns True if the platform is OS X. '''
    return platform.system() == 'Darwin'

