# -*- coding: utf-8 -*-

from nimp.commands._command     import *
from nimp.utilities.packaging   import *

#-------------------------------------------------------------------------------
class PackageCommand(Command):
    def __init__(self):
        Command.__init__(self, 'package', 'Packages game')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('loose_files_directory',
                            help    = 'Loose files directory.',
                            metavar = '<DIR>')

        parser.add_argument('packages_directory',
                            help    = 'Destination directory for packages.',
                            metavar = '<DIR>',
                            default = '.')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'Platform to generate packages for',
                            metavar = '<platform>')

        parser.add_argument('--dlc',
                            help    = 'Dlc to pack',
                            metavar = '<dlc>',
                            default = None)

        parser.add_argument('--config-only',
                            help    = 'Only generate package config files',
                            action  = "store_true",
                            default = False)

        parser.add_argument('--package-only',
                            help    = 'Use existing package config files',
                            action  = "store_true",
                            default = False)
        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        if not env.package_only:
            if not generate_pkg_config(env, env.loose_files_directory):
                return False
        if not env.config_only:
            if not make_packages(env, env.loose_files_directory, env.packages_directory):
                return False
        return True