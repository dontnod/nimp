# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.perforce import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisCommand(Command):
    abstract = 1 # Vieux hackos pour que l'introspection n'instancie pas cette
                 # classe, on pourrait checker que le module ne commence pas par _

    #-------------------------------------------------------------------------
    def __init__(self, name, description):
        Command.__init__(self, name, description)

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('p4_client',
                            metavar = '<CLIENT_NAME>',
                            type    = str)

        parser.add_argument('--local',
                            help    = "Don't touch workspace or P4 settings.",
                            action  = "store_true",
                            default = False)

        parser.add_argument('--patch-config',
                            help    = 'Patch config file',
                            metavar = '<PATH>',
                            default = None)

        parser.add_argument('--hard-clean',
                            help    = 'Remove all unversionned files',
                            action  = "store_true",
                            default = False)

        return self.cis_configure_arguments(env, parser)

    #---------------------------------------------------------------------------
    def cis_configure_arguments(self, env, parser):
        return False

    #---------------------------------------------------------------------------
    def run(self, env):
        if not self._setup_perforce(env):
            log_error("Error setuping perforce workspace")
            return False

        result = self._cis_run(env)

        if not env.local:
            p4_clean_workspace()

        return result

    def _cis_run(self, env):
        return False

    def _setup_perforce(self, env):
        if not env.local:
            if not p4_create_config_file(FARM_P4_PORT, FARM_P4_USER, FARM_P4_PASSWORD, env.p4_client):
                return False

            if not p4_clean_workspace():
                return False

        if env.patch_config is not None and env.patch_config != "None":
            if not env.load_config_file(env.patch_config):
                log_error("Error while loading patch config file {0}, aborting...", env.patch_config)
                return False
            for file_path, revision in env.patch_files_revisions:
                log_notification("Syncing file {0} to revision {1}", file_path, revision)
                if not p4_sync(file_path, revision):
                    return False
                if file_path == ".nimp.conf":
                    log_notification("Reloading config...")
                    if not env.load_config_file(".nimp.conf"):
                        return False
        return True

