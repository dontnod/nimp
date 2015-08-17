# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *
from nimp.utilities.deployment import *
from nimp.utilities.file_mapper import *

#-------------------------------------------------------------------------------
class DeployCommand(Command):
    def __init__(self):
        Command.__init__(self,
                         'deploy',
                         'Deployment command')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('-m',
                            '--mode',
                            help = 'operating mode (binaries, version, cook)',
                            metavar = '<mode>')

        parser.add_argument('-r',
                            '--revision',
                            help = 'revision',
                            metavar = '<revision>')

        parser.add_argument('--platform',
                   help = 'Platform to deploy',
                   metavar = '<platform>')

        parser.add_argument('--configuration',
                   help = 'Configuration to deploy',
                   metavar = '<config>')

        parser.add_argument('--max-revision',
                   help = 'Find a revision <= to this',
                   metavar = '<revision>')

        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        files_to_deploy = env.map_files()
        if not hasattr(env, 'mode') or env.mode == 'binaries':
            log_notification(log_prefix() + "Deploying Binaries…")
            files_to_deploy.to('.').src(env.publish_binaries).glob("**").files()

        elif env.mode == 'version':
            src = env.publish_version
            if env.max_revision is not None:
                revision = get_latest_available_revision(env, src, **vars(env))
                if revision is None:
                    return False
                env.revision = revision
            log_notification(log_prefix() + "Deploying version…")
            files_to_deploy.to('.').src(src).glob("**").files()

        elif env.mode == 'cook':
            log_error("Not implemented yet...")
            return False

        cl_number = p4_get_or_create_changelist('Deployment')
        if cl_number is None:
            return False

        files = list(files_to_deploy())
        dst_files = [dst for src, dst in files]
        p4_edit(cl_number, *dst_files)

        for src, dst in files:
            print('Copying ' + src)
            if not robocopy(src, dst):
                return False

        return True

