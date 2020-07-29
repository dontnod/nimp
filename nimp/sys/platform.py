
''' Platform-related configuration utilities '''

import logging
import platform
import pkg_resources

import nimp.base_platforms

from nimp.utils.python import get_class_instances


_all_platforms = {}


class Platform:
    ''' Describe a platform and its specific quirks '''

    def __init__(self):
        self.name = 'null'
        self.aliases = set()

        ''' Packaging information '''
        self.layout_file_extension = 'txt'
        self.ue4_package_directory = '{uproject_dir}/Saved/Packages/{cook_platform}'


def create_platform_desc(name):
    ''' Create a platform description from a short name (ps4, win64, …) '''
    if name not in _all_platforms:
        logging.warn(f'No support for platform {name}')
        return Platform()
    return _all_platforms[name]


def discover(env):
    ''' Import platforms from base nimp and from plugins '''

    tmp = {}
    get_class_instances(nimp.base_platforms, Platform, tmp)

    for e in pkg_resources.iter_entry_points('nimp.plugins'):
        get_class_instances(e, Platform, tmp)

    # Register platform classes under their names and aliases
    for platform in tmp.values():
        for n in [platform.name, *platform.aliases]:
            _all_platforms[n] = platform


def is_windows():
    ''' Return True if the runtime platform is Windows, including MSYS '''
    return is_msys() or platform.system() == 'Windows'

def is_msys():
    ''' Returns True if the platform is msys. '''
    return platform.system()[0:7] == 'MSYS_NT'

def is_osx():
    ''' Returns True if the platform is OS X. '''
    return platform.system() == 'Darwin'

