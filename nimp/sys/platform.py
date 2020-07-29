
''' Platform-related configuration utilities '''

import abc
import logging
import platform
import pkg_resources

import nimp.base_platforms

from nimp.utils.python import get_class_instances


_all_platforms = {}


class Platform(metaclass=abc.ABCMeta):
    ''' Describe a platform and its specific quirks '''

    def __init__(self):
        self.name = None
        self.aliases = set()

        self.is_valid = True
        self.is_microsoft = False
        self.is_sony = False
        self.is_mobile = False

        ''' Packaging information '''
        self.layout_file_extension = 'txt'
        self.ue4_package_directory = '{uproject_dir}/Saved/Packages/{cook_platform}'
        self.ue4_name = None


class NullPlatform(Platform):
    def __init__(self):
        super().__init__()
        self.name = 'null'
        self.ue4_name = 'Null'
        self.is_valid = False


def create_platform_desc(name):
    ''' Create a platform description from a short name (ps4, win64, …) '''
    if name not in _all_platforms:
        logging.warn(f'No nimp support for platform {name}')
        return NullPlatform()
    return _all_platforms[name]


def discover(env):
    ''' Import platforms from base nimp and from plugins '''

    tmp = {}
    get_class_instances(nimp.base_platforms, Platform, tmp)

    for e in pkg_resources.iter_entry_points('nimp.plugins'):
        get_class_instances(e, Platform, tmp)

    for platform in tmp.values():

        # Set env.is_win32, env.is_linux, etc. to False by default
        setattr(env, f'is_{platform.name}', False)

        # Register platform classes under their names and aliases
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

