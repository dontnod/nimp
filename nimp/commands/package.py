# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.processes import *
from nimp.utilities.ps3 import *
from nimp.utilities.ps4 import *
from nimp.utilities.xboxone import *

#-------------------------------------------------------------------------------
class PackageCommand(Command):
    def __init__(self):
        Command.__init__(self, 'package', 'Packages game, patch or DLC')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('-c',
                            '--configuration',
                            help    = 'Configuration to publish',
                            metavar = '<configuration>')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'Platform to generate packages for',
                            metavar = '<platform>')

        parser.add_argument('-r',
                            '--revision',
                            help = 'revision',
                            metavar = '<revision>')

        parser.add_argument('--dlc',
                            help    = 'DLC to pack',
                            metavar = '<dlc>',
                            default = None)

        # FIXME: env.is_ue4 is not present at this time, but we want it
        if hasattr(env, 'project_type') and env.project_type is 'UE4':
            parser.add_argument('destination',
                                help    = 'Destination Directory',
                                metavar = '<DIR>')

        if hasattr(env, 'project_type') and env.project_type is 'UE3':
            parser.add_argument('--loose-files-directory',
                                help    = 'Loose files destination Directory',
                                metavar = '<LOOSE_FILES_DIRECTORY>')

            parser.add_argument('--packages-directory',
                                help    = 'Packages destination Directory',
                                metavar = '<PACKAGES_DIRECTORY>')

            parser.add_argument('--only-packages',
                                help    = 'Use existing loose files to build packages',
                                action  = "store_true",
                                default = False)

            parser.add_argument('--no-packages',
                                help    = 'Don’t build console packages',
                                action  = "store_true",
                                default = False)

        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        loose_dir = env.format(env.loose_files_directory) if env.loose_files_directory else env.publish_ship
        pkg_dir = env.format(env.packages_directory) if env.packages_directory else env.publish_pkgs

        # Generate package configuration (.gp4, .xml, etc.)
        if not env.only_packages:

            # Everywhere except Win32
            if not env.is_win32:
                if not _load_package_config(env):
                    return False

            # Only on PS4
            if env.is_ps4:
                if not generate_gp4(env, loose_dir):
                    return False
            elif env.is_xone:
                if not generate_chunk_xml(env, loose_dir):
                    return False

        # Generate the packages themselves
        if not env.no_packages:

            # Everywhere except Win32
            if not env.is_win32:
                if not _load_package_config(env):
                    return False

            if env.is_ps3:
                if not ps3_generate_pkgs(env, loose_dir, pkg_dir):
                    return False
            elif env.is_ps4:
                if not ps4_generate_pkgs(env, loose_dir, pkg_dir):
                    return False
            elif env.is_xone:
                if not xboxone_generate_pkgs(env, loose_dir, pkg_dir):
                    return False

        return True


def _load_package_config(env):
    if not env.check_keys('packages_config_file'):
        return False

    package_config = env.format(env.packages_config_file)

    if not env.load_config_file(package_config):
        return False
    return True

