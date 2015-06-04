# -*- coding: utf-8 -*-

from nimp.commands._cis_command import *
from nimp.utilities.ue3         import *
from nimp.utilities.deployment  import *
from nimp.utilities.packaging   import *

#-------------------------------------------------------------------------------
class CisUe3Ship(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-ue3-ship', 'Cooks and publish a final version.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        CisCommand.configure_arguments(self, env, parser)

        parser.add_argument('-r',
                            '--revision',
                            help    = 'Current revision',
                            metavar = '<revision>',
                            default = None)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to publish',
                            metavar = '<platform>')

        parser.add_argument('--dlc',
                            help    = 'Dlc to cook',
                            metavar = '<dlc>',
                            default = None)
        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, env):
        platforms = ["Win64"]

        if not env.is_win64:
            platforms += [env.platform]

        with deploy_latest_revision(env, env.publish_version, env.revision, platforms):
            if env.dlc != env.project:
                master_files = env.map_files()
                master_files.override(dlc = env.project).src(env.publish_cook).recursive().files()
                log_notification(log_prefix() + "Deploying episode01 cook…")
                if not all_map(robocopy, master_files()):
                    return False

            if not ue3_ship(env):
                return False
            if not generate_pkg_config(env):
                return False
            if not make_packages(env):
                return False

        return True
