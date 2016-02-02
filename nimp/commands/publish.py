# -*- coding: utf-8 -*-

import shutil
import zipfile

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *
from nimp.utilities.deployment import *
from nimp.utilities.symbols import *
from nimp.utilities.file_mapper import *
from nimp.utilities.paths import *
from nimp.utilities.torrent import *

#-------------------------------------------------------------------------------
class PublishCommand(Command):
    def __init__(self):
        Command.__init__(self,
                         'publish',
                         'Publish binaries or symbols')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('-m', '--mode',
                            help = 'operating mode (binaries, symbols, version)',
                            metavar = '<mode>')

        parser.add_argument('-p', '--platform',
                            help = 'platforms to publish',
                            metavar = '<platform>')

        parser.add_argument('-c', '--configuration',
                            help = 'configuration to publish',
                            metavar = '<configuration>')

        parser.add_argument('-t', '--target',
                            help = 'target to publish (game, editor, tools)',
                            metavar = '<target>')

        # FIXME: could we avoid this argument? right now we need it for upload_symbols
        parser.add_argument('-r',
                            '--revision',
                            help = 'revision',
                            metavar = '<revision>')

        # FIXME: this looks too much like --configuration! do something about it
        parser.add_argument('-l',
                            '--configurations',
                            help    = 'Configurations and targets to deploy',
                            metavar = '<configurations>',
                            nargs = '+')

        return True

    #---------------------------------------------------------------------------
    def run(self, env):

        files_to_publish = env.map_files()

        if not hasattr(env, 'mode') or env.mode == 'binaries':
            log_notification("Publishing binaries…")
            files_to_publish.to(env.publish_binaries).load_set("binaries")
            if not all_map(robocopy, files_to_publish()):
                return False

        elif env.mode == 'symbols':
            log_notification("Publishing symbols…")
            symbols_to_publish = env.map_files()
            symbols_to_publish.load_set("symbols")
            if not upload_symbols(env, symbols_to_publish()):
                return False

        elif env.mode == 'version':
            log_notification("Publishing version…")

            files_to_deploy = env.map_files().to(env.format(env.root_dir))

            for config_or_target in env.configurations:

                c = config_or_target if config_or_target not in ['editor', 'tools'] else 'devel'
                t = config_or_target if config_or_target in ['editor', 'tools'] else 'game'

                if env.is_ue3:
                    tmp = files_to_deploy.override(configuration = c,
                                                   target = t,
                                                   ue3_build_configuration = get_ue3_build_config(c))
                elif env.is_ue4:
                    tmp = files_to_deploy.override(configuration = c,
                                                   target = t,
                                                   ue4_build_configuration = get_ue4_build_config(c))

                tmp = tmp.src(env.publish_binaries)

                # UE4 only? FIXME: the logic here doesn’t seem sane to me…
                #if hasattr(env, 'deploy_version_root'):
                #    tmp.to(env.deploy_version_root).glob("**")

                tmp.glob("**")

            log_notification("Deploying binaries…")
            if not all_map(robocopy, files_to_deploy()):
                return False

            # Only for Unreal Engine 3: build scripts
            if env.is_ue3 and env.is_win64:
                log_notification("Building script…")
                if not ue3_build_script(env.game):
                    log_error("Error while building script")
                    return False

            log_notification("Publishing version {0}…", env.publish_version)
            files_to_publish.to(env.format(env.publish_version)).load_set("version")
            if not all_map(robocopy, files_to_publish()):
                return False

            # Create a Torrent
            if hasattr(env, 'torrent_path'):
                torrent = env.format(env.torrent_path)

                log_notification("Creating torrent {0}…", torrent)

                # If torrent root is “a/b/c”, publish it to “b/c” with root dir “a”
                tree = path_to_array(env.format(env.torrent_root))
                publish_torrent = env.map_files()
                publish_torrent.to('/'.join(tree[1:])).load_set("version")

                data = make_torrent(tree[0], env.torrent_tracker, publish_torrent)
                if not data:
                    log_error("Torrent is empty")
                    return False

                with open(sanitize_path(torrent), 'wb') as fd:
                    fd.write(data)

            # Create a Zip file
            if hasattr(env, 'torrent_root'):
                zipf = env.format(env.publish_version + '.zip')

                log_notification('Creating Zip file {0}…', zipf)

                zfd = zipfile.ZipFile(sanitize_path(zipf), 'w')
                publish_torrent = env.map_files()
                publish_torrent.to('.').load_set('version')
                for src, dst in publish_torrent():
                    if os.path.isfile(src):
                         log_notification('Adding {0} as {1}', src, dst)
                         zfd.write(src, dst)
                zfd.close()

        return True

