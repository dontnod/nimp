# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *
from nimp.utilities.packaging import *

#-------------------------------------------------------------------------------
class ShipCommand(Command):
    def __init__(self):
        Command.__init__(self, 'ship', 'Generate shippable loose files in target directory')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('-p',
                            '--platform',
                            help    = 'Platforms to publish',
                            metavar = '<platform>')

        parser.add_argument('--dlc',
                            help    = 'DLCs to ship',
                            metavar = '<dlc>',
                            default = None)

        # FIXME: env.is_ue4 is not present at this time, but we want it
        if hasattr(env, 'project_type') and env.project_type is 'UE4':
            parser.add_argument('destination',
                                help    = 'Destination Directory',
                                metavar = '<DIR>')

        if hasattr(env, 'project_type') and env.project_type is 'UE3':
            parser.add_argument('--loose-dir',
                                help    = 'Loose files destination Directory',
                                metavar = '<LOOSE_FILES_DIRECTORY>')

            parser.add_argument('--pkg-dir',
                                help    = 'Packages destination Directory',
                                metavar = '<PACKAGES_DIRECTORY>')

            parser.add_argument('--packages-only',
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

        # Unreal Engine 4
        if env.is_ue4:
            return ue4_ship(env, env.destination)

        # Unreal Engine 3
        if env.is_ue3:
            loose_files_dir = env.format(env.loose_dir)
            pkgs_dir = env.format(env.pkg_dir)

            if not env.packages_only:
                if not ue3_ship(env, loose_files_dir):
                    return False
                if not generate_pkg_config(env, loose_files_dir):
                    return False

            if not env.no_packages:
                if not make_packages(env, loose_files_dir, pkgs_dir):
                    return False

            return True

        # Error!
        log_error(log_prefix() + "Invalid project type {0}" % (env.project_type))
        return False

