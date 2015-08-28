# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *
from nimp.utilities.packaging import *
from nimp.utilities.file_mapper import *

#-------------------------------------------------------------------------------
class ShipCommand(Command):
    def __init__(self):
        Command.__init__(self, 'ship', 'Generate shippable loose files in target directory')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('-c',
                            '--configuration',
                            help    = 'Configuration to publish',
                            metavar = '<configuration>')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'Platforms to publish',
                            metavar = '<platform>')

        parser.add_argument('--dlc',
                            help    = 'DLCs to ship',
                            metavar = '<dlc>',
                            default = None)

        parser.add_argument('-r',
                            '--revision',
                            help = 'revision',
                            metavar = '<revision>')

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

        # Unreal Engine 4
        if env.is_ue4:
            return ue4_ship(env, env.destination)

        # Unreal Engine 3
        if env.is_ue3:

            loose_files_dir = env.format(env.loose_dir) if env.loose_dir else None
            pkgs_dir = env.format(env.pkg_dir) if env.pkg_dir else None

            ship_game = (env.dlc == 'main')
            ship_incremental = os.path.exists(env.format(env.publish_master))

            if not env.only_packages:
                log_notification(log_prefix() + "Performing UE3 ship… game:%d incremental:%d"
                                                % (ship_game, ship_incremental))

                if ship_incremental and not ship_game:
                    log_error(log_prefix() + "Sorry, building a DLC patch is still not implemented")
                    return False

                # If cooking a DLC or a patch, we first need the original cook;
                # either the master cook (when shipping a game patch) or one of
                # the latest cooks done by buildbot
                if ship_incremental or not ship_game:
                    log_notification(log_prefix() + "Deploying original cook…")
                    master_files = env.map_files()
                    if ship_game:
                        master_files_source = master_files.src(env.publish_master) \
                                                          .recursive() \
                                                          .files()
                    else:
                        master_files_source = master_files.override(dlc = 'main', revision = 'HEAD') \
                                                          .src(env.publish_cook) \
                                                          .recursive() \
                                                          .files()
                    if not all_map(robocopy, master_files()):
                        return False

                # Now we can cook the desired maps
                maps = env.cook_maps[env.dlc.lower()]

                log_notification(log_prefix() + "Cooking maps: %s" % (" ".join(maps)))
                if not ue3_cook(env.game,
                                maps,
                                env.languages,
                                env.dlc,
                                env.ue3_cook_platform,
                                env.configuration,
                                incremental = ship_game and ship_incremental):
                    return False

                # If necessary, overwrite files we didn’t want to patch from the master again
                if ship_game and ship_incremental:
                        log_notification(log_prefix() + "Redeploying master cook ignoring patched files…")
                        patch_files = env.map_files()
                        patch_files.src(env.publish_master).override(step = 'patching').load_set("patch")
                        files_to_exclude = [src for src, *args in patch_files()]
                        log_notification(log_prefix() + "Excluding files %s" % (files_to_exclude))
                        master_files_source.exclude_ignore_case(*files_to_exclude)
                        if not all_map(robocopy, master_files()):
                            return False

            if not env.only_packages:
                # Publish cooked directory to env.publish_cook
                if ship_game and hasattr(env, 'revision'):
                    cook_files = env.map_files()
                    cook_files.to(env.publish_cook).load_set("cook")
                    if not all_map(robocopy, cook_files()):
                        return False

            if not env.only_packages:
                # Publish final files to env.publish_ship
                destination = loose_files_dir or env.publish_ship

                if ship_game:
                    # PS3-specific step
                    if env.is_ps3:
                        ue3_generate_ps3_binaries(env)

                    if not ship_incremental:
                        # FIXME: implement this!
                        log_warning(log_prefix() + "Publishing full game is not implemented")
                    else:
                        log_notification(log_prefix() + "Copying files to output directory…")
                        patch_files = env.map_files()
                        patch_files.to(destination).override(step = 'deploy').load_set("patch")
                        if not all_map(robocopy, patch_files()):
                            return False

                        # Win32-specific step
                        if env.is_win32:
                            ue3_fix_pc_ini(env, destination)
                else:
                    log_notification(log_prefix() + "Copying DLC to output directory…")
                    dlc_files = env.map_files()
                    dlc_files.to(destination).load_set("dlc")

                    if not all_map(robocopy, dlc_files()):
                        return False

            if not env.no_packages:
                # Generate package configuration
                log_notification(log_prefix() + "Generating package config…")
                if not generate_pkg_config(env, loose_files_dir):
                    return False

                # Generate packages
                log_notification(log_prefix() + "Building packages…")
                if not make_packages(env, loose_files_dir, pkgs_dir):
                    return False

            return True

        # Error!
        log_error(log_prefix() + "Invalid project type %s" % (env.project_type))
        return False

