# -*- coding: utf-8 -*-

from nimp.commands.command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *
from nimp.utilities.file_mapper import *
from nimp.utilities.ps3 import *

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

        parser.add_argument('-r',
                            '--revision',
                            help = 'revision',
                            metavar = '<revision>')

        parser.add_argument('--dlc',
                            help    = 'DLCs to ship',
                            metavar = '<dlc>',
                            default = None)

        # FIXME: env.is_ue4 is not present at this time, but we want it
        if hasattr(env, 'project_type') and env.project_type is 'UE4':
            parser.add_argument('--destination',
                                help    = 'Destination Directory',
                                metavar = '<DIR>')

        if hasattr(env, 'project_type') and env.project_type is 'UE3':
            parser.add_argument('--loose-files-directory',
                                help    = 'Loose files destination Directory',
                                metavar = '<LOOSE_FILES_DIRECTORY>')

            parser.add_argument('--packages-directory',
                                help    = 'Packages destination Directory',
                                metavar = '<PACKAGES_DIRECTORY>')

        parser.add_argument('--no-cook',
                            help = 'Do not cook, assume everything is in place',
                            action = "store_true",
                            default = False)

        return True


    #---------------------------------------------------------------------------
    def run(self, env):

        # Unreal Engine 4
        if env.is_ue4:
            loose_dir = env.format(env.destination) if env.destination else env.format(env.publish_ship)
            exe_path = sanitize_path(os.path.join(env.format(env.root_dir), "Engine/Binaries/DotNET/AutomationTool.exe"))
            # Use heartbeat because this sometimes compiles shaders in the background
            if 0 != call_process('.',
                                 [exe_path,
                                  "BuildCookRun",
                                  "-nocompileeditor", "-nop4",
                                  sanitize_path(env.format("-project={game}/{game}.uproject")),
                                  "-cook", "-stage", "-archive",
                                  "-archivedirectory=%s" % sanitize_path(loose_dir),
                                  "-package",
                                  "-clientconfig=%s" % env.configuration,
                                  "-ue4exe=UE4Editor-Cmd.exe",
                                  "-pak",
                                  "-prereqs",
                                  "-nodebuginfo",
                                  env.format("-targetplatform={ue4_cook_platform}"),
                                  "-utf8output"],
                                 heartbeat = 30):
                return False
            return True

        # Unreal Engine 3
        if env.is_ue3:

            loose_dir = env.format(env.loose_files_directory) if env.loose_files_directory else env.publish_ship
            loose_dir = sanitize_path(loose_dir)
            log_notification("Looking for master in %s" % (sanitize_path(env.format(env.publish_master))))

            ship_game = (env.dlc == 'main')
            ship_incremental = os.path.exists(sanitize_path(env.format(env.publish_master)))

            if not env.no_cook:
                log_notification("Performing UE3 ship… game:%d incremental:%d" % (ship_game, ship_incremental))

                if ship_incremental and not ship_game:
                    log_error("Building a DLC patch is still not implemented")
                    return False

                # If cooking a DLC or a patch, we first need the original cook;
                # either the master cook (when shipping a game patch) or one of
                # the latest cooks done by buildbot
                if ship_incremental or not ship_game:
                    log_notification("Deploying original cook…")
                    master_files = env.map_files()
                    if ship_game:
                        master_files_source = master_files.src(sanitize_path(env.publish_master)) \
                                                          .recursive() \
                                                          .files()
                    else:
                        master_files_source = master_files.override(dlc = 'main', revision = 'HEAD') \
                                                          .src(sanitize_path(env.publish_cook)) \
                                                          .recursive() \
                                                          .files()
                    if not all_map(robocopy, master_files()):
                        return False

                # Now we can cook the desired maps
                maps = env.cook_maps[env.dlc.lower()]

                log_notification("Cooking maps: %s" % (" ".join(maps)))
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
                    log_notification("Redeploying master cook ignoring patched files…")
                    patch_files = env.map_files()
                    patch_files.src(sanitize_path(env.publish_master)).override(step = 'patching').load_set("patch")
                    files_to_exclude = [src for src, *args in patch_files()]

                    for f in files_to_exclude:
                        log_notification("Will exclude: %s" % (f))

                    master_files_source.exclude_ignore_case(*files_to_exclude)
                    if not all_map(robocopy, master_files()):
                        return False

            if True:
                # Publish cooked directory to env.publish_cook
                if ship_game and hasattr(env, 'revision'):
                    cook_files = env.map_files()
                    cook_files.to(sanitize_path(env.publish_cook)).load_set("cook")
                    if not all_map(robocopy, cook_files()):
                        return False

            if True:
                # Publish final files to env.publish_ship
                if ship_game:
                    # PS3-specific step
                    if env.is_ps3:
                        ue3_generate_ps3_binaries(env)

                    if not ship_incremental:
                        # FIXME: implement this!
                        log_warning("Publishing full game is not implemented")
                    else:
                        log_notification("Copying files to output directory…")
                        patch_files = env.map_files()
                        patch_files.to(loose_dir).override(step = 'deploy').load_set("patch")
                        if not all_map(robocopy, patch_files()):
                            return False

                        # Win32-specific step
                        if env.is_win32:
                            ue3_fix_pc_ini(env, os.path.join(loose_dir, "Episode01"))
                else:
                    log_notification("Copying DLC to output directory…")
                    dlc_files = env.map_files()
                    dlc_files.to(loose_dir).load_set("dlc")

                    if not all_map(robocopy, dlc_files()):
                        return False

                if env.is_ps3:
                    ps3_generate_edata(env, loose_dir)
            return True

        # Error!
        log_error("Invalid project type %s" % (env.project_type))
        return False

