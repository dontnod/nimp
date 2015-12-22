# -*- coding: utf-8 -*-

import shutil

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *
from nimp.utilities.deployment import *
from nimp.utilities.symbols import *
from nimp.utilities.file_mapper import *

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

        parser.add_argument('--keep-temp-binaries',
                            help    = 'Don’t delete temporary binaries directory',
                            action  = "store_true",
                            default = False)

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

            publish_version_path = env.format(env.publish_version)
            log_notification("Publishing version {0}…", env.publish_version)
            files_to_publish.to(publish_version_path).load_set("version")
            if not all_map(robocopy, files_to_publish()):
                return False

            # Support UnrealProp if necessary
            if hasattr(env, 'unreal_prop_path') and hasattr(env, 'upms_platform'):
                unreal_prop_path = env.format(env.unreal_prop_path)
                publish_to_unreal_prop = env.map_files()
                publish_to_unreal_prop.override(is_unreal_prop_version = True).to(unreal_prop_path).load_set("version")
                log_notification("Copying files to unreal prop…")

                if not all_map(robocopy, publish_to_unreal_prop()):
                    return False

                # Patoune wants this file
                cl_name = 'CL.txt'
                log_notification("Writing changelist file {0} for {1}…", cl_name, env.publish_version)
                cl_path = sanitize_path(os.path.join(unreal_prop_path, cl_name))
                with open(cl_path, "w") as cl_fd:
                    cl_fd.write('%s\n' % env.revision)

                # Many Epic tools only consider the build valid if they find a *TOC.txt file
                # See for instance GetLatestBuildFromUnrealProp() in CIS Build Controller
                # Also, Patoune insists on having a specific TOC name, hence the toc_name part
                if hasattr(env, 'game'):
                    if env.is_ue3:
                        toc_name = '%s%sTOC.txt' % (env.upms_platform, 'FINAL' if env.is_win32 else '')
                        toc_content = ''
                    elif env.is_ue4:
                        toc_name = 'TOC.xml'
                        toc_content = '<lol></lol>\n'

                    log_notification("Writing fake TOC {0} for UnrealProp", toc_name)

                    toc_dir = os.path.join(unreal_prop_path, env.game)
                    safe_makedirs(toc_dir)

                    toc_path = sanitize_path(os.path.join(toc_dir, toc_name))
                    with open(toc_path, "w") as toc_fd:
                        toc_fd.write(toc_content)

            # If everything went well, remove temporary binaries
            if not env.keep_temp_binaries:
                for config_or_target in env.configurations:

                    c = config_or_target if config_or_target not in ['editor', 'tools'] else 'devel'
                    t = config_or_target if config_or_target in ['editor', 'tools'] else 'game'

                    try:
                        path = env.format(env.publish_binaries,
                                          configuration = c,
                                          target = t)
                        shutil.rmtree(sanitize_path(path))
                    except Exception as ex:
                        log_error("Error while cleaning binaries: {0}", ex)

        return True

