
''' Platform-related configuration utilities '''

import platform
import pkg_resources

import nimp.base_platforms

from nimp.utils.python import get_class_instances


_all_platforms = {}


class Platform:
    def __init__(self):
        pass


def discover(env):
    ''' Import platforms from base nimp and from plugins '''

    get_class_instances(nimp.base_platforms, Platform, _all_platforms)

    for e in pkg_resources.iter_entry_points('nimp.plugins'):
        get_class_instances(e, Platform, _all_platforms)

    for platform in _all_platforms.values():
        platform.register(env)


def is_windows():
    ''' Return True if the runtime platform is Windows, including MSYS '''
    return is_msys() or platform.system() == 'Windows'

def is_msys():
    ''' Returns True if the platform is msys. '''
    return platform.system()[0:7] == 'MSYS_NT'

def is_osx():
    ''' Returns True if the platform is OS X. '''
    return platform.system() == 'Darwin'

