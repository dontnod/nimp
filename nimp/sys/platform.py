
''' Platform-related configuration utilities '''

import abc
import logging
import platform
import pkg_resources

import nimp.base_platforms

from nimp.utils.python import get_class_instances

_all_platforms = {}
_all_aliases = {}
_all_unreal_platforms = {}


class Platform(metaclass=abc.ABCMeta):
    ''' Describe a platform and its specific quirks '''

    def __init__(self, env):
        self.name = None
        self.aliases = set()

        self.is_valid = True
        self.is_microsoft = False
        self.is_sony = False
        self.is_nintendo = False
        self.is_mobile = False

        ''' Packaging information '''
        self.layout_file_extension = 'txt'
        self.package_tool_path = None
        self.unreal_package_directory = '{uproject_dir}/Saved/Packages/{cook_platform}'
        self.unreal_name = None
        self.unreal_config_name = None
        self.unreal_cook_name = None

    def install_package(self, package_directory, env):
        return False

    def launch_package(self, package_name, env):
        return False


class NullPlatform(Platform):
    def __init__(self, env=None):
        super().__init__(env)
        self.name = 'null'
        self.unreal_name = 'Null'
        self.unreal_config_name = 'Null'
        self.unreal_cook_name = 'Null'
        self.is_valid = False


def create_platform_desc(name):
    ''' Create a platform description from a short name (ps4, win64, …) '''
    if name not in _all_aliases:
        logging.warn(f'No nimp support for platform {name}')
        return NullPlatform()
    return _all_platforms[_all_aliases[name]]


def create_platform_desc_unreal(unreal_name):
    ''' Create a platform description from a Unreal name (PS4, Win64, …) '''
    if unreal_name not in _all_unreal_platforms:
        logging.warn(f'No Unreal support for platform {unreal_name}')
        return NullPlatform()
    return _all_unreal_platforms[unreal_name]
    


def discover(env):
    ''' Import platforms from base nimp and from plugins '''

    tmp = {}
    get_class_instances(nimp.base_platforms, Platform, tmp, instance_args=[env])

    for e in pkg_resources.iter_entry_points('nimp.plugins'):
        try:
            module = e.load()
            get_class_instances(module, Platform, tmp, instance_args=[env])
        except:
            pass

    for platform in tmp.values():

        # Set env.is_win32, env.is_linux, etc. to False by default
        setattr(env, f'is_{platform.name}', False)

        # Register platform classes under their names and aliases
        _all_platforms[platform.name] = platform
        _all_unreal_platforms[platform.unreal_name] = platform

        for n in [platform.name, *platform.aliases]:
            _all_aliases[n] = platform.name


def is_windows():
    ''' Return True if the runtime platform is Windows, including MSYS '''
    return is_msys() or platform.system() == 'Windows'

def is_msys():
    ''' Returns True if the platform is msys. '''
    return platform.system()[0:7] == 'MSYS_NT'

def is_osx():
    ''' Returns True if the platform is OS X. '''
    return platform.system() == 'Darwin'

