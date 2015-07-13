# -*- coding: utf-8 -*-

import shutil

from nimp.commands._cis_command import *
from nimp.utilities.ue3         import *
from nimp.utilities.ue4         import *
from nimp.utilities.file_mapper import *
from nimp.utilities.deployment  import *

FARM_P4_PORT     = "farmproxy:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisPublish(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-publish', 'Gets built binaries and publishes an internal version.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        CisCommand.configure_arguments(self, env, parser)
        parser.add_argument('-r',
                            '--revision',
                            help    = 'Current revision',
                            metavar = '<revision>')

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to build',
                            metavar = '<platform>')

        parser.add_argument('-c',
                            '--configurations',
                            help    = 'Configurations to deploy',
                            metavar = '<configurations>',
                            nargs = '+')

        parser.add_argument('--keep-temp-binaries',
                            help    = 'Don’t delete temporary binaries directory',
                            action  = "store_true",
                            default = False)
        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, env):
        with p4_transaction("Binaries Checkout",
                            submit_on_success = False,
                            revert_unchanged = False,
                            add_not_versioned_files = False) as trans:

            files_to_deploy = env.map_files().to('.')

            for configuration in env.configurations:
                if hasattr(env, 'project_type') and env.project_type is 'UE3':
                    tmp = files_to_deploy.override(configuration = configuration,
                                                   ue3_build_configuration = get_ue3_build_config(configuration))
                else:
                    tmp = files_to_deploy.override(configuration = configuration,
                                                   ue4_build_configuration = get_ue4_build_config(configuration, env.platform))

                tmp.src(env.publish_binaries)

                # UE4 only? FIXME: the logic here doesn’t seem sane to me…
                #if hasattr(env, 'deploy_version_root'):
                #    tmp.to(env.deploy_version_root).glob("**")

                tmp.glob("**")

            log_notification(log_prefix() + "Deploying binaries…")
            if not all_map(checkout_and_copy(trans), files_to_deploy()):
                return False

            if not env.keep_temp_binaries:
                for configuration in env.configurations:
                    try:
                        shutil.rmtree(env.format(env.publish_binaries, configuration = configuration))
                    except Exception as ex:
                        log_error(log_prefix() + "Error while cleaning binaries : {0}", ex)

            # Only for Unreal Engine 3: build scripts
            if hasattr(env, 'project_type') and env.project_type is 'UE3':
                if env.is_win64:
                    log_notification(log_prefix() + "Building script…")
                    if not ue3_build_script(env.game):
                        log_error(log_prefix() + "Error while building script")
                        return False

            publish_version_path = env.format(env.publish_version)
            files_to_publish = env.map_files().to(publish_version_path)
            log_notification(log_prefix() + "Publishing version {0}…", configuration)
            files_to_publish.load_set("version")
            if not all_map(robocopy, files_to_publish()):
                return False

            # Only for Unreal Engine 4: unrealprop
            if hasattr(env, 'project_type') and env.project_type is 'UE4':
                if hasattr(env, 'unreal_prop_path'):
                    unreal_prop_path = env.format(env.unreal_prop_path)
                    publish_to_unreal_prop = env.map_files().override(is_unreal_prop_version = True).to(unreal_prop_path)
                    log_notification(log_prefix() + "Copying files to unreal prop…")
                    publish_to_unreal_prop.load_set("version")

                    if not all_map(robocopy, publish_to_unreal_prop()):
                        return False

                    log_notification(log_prefix() + "Writing CL.txt file {0}…", configuration)
                    if hasattr(env, 'cl_txt_path'):
                        cl_txt_path = os.path.join(unreal_prop_path, env.cl_txt_path)
                        with open(cl_txt_path, "w") as cl_txt_file:
                            cl_txt_file.write("%s\n" % env.revision)

        return True

