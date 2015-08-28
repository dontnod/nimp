# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.packaging import *

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
            parser.add_argument('loose_files_directory',
                                help    = 'Loose files destination Directory',
                                metavar = '<LOOSE_FILES_DIRECTORY>')

            parser.add_argument('packages_directory',
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

        loose_dir = env.format(env.loose_files_directory) if env.loose_files_directory else None
        pkg_dir = env.format(env.packages_directory) if env.packages_directory else None

        if not env.only_packages:
            if not generate_pkg_config(env, loose_dir):
                return False

        if not env.no_packages:
            if not make_packages(env, loose_dir, pkg_dir):
                return False

        return True

