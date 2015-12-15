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
        parser.add_argument('-m', '--mode',
                            help = 'operating mode (binaries, version, cook)',
                            metavar = '<mode>')

        parser.add_argument('-r', '--revision',
                            help = 'revision',
                            metavar = '<revision>')

        parser.add_argument('-p', '--platform',
                            help = 'platform to deploy',
                            metavar = '<platform>')

        parser.add_argument('-c', '--configuration',
                            help = 'configuration to deploy',
                            metavar = '<config>')

        parser.add_argument('-t', '--target',
                            help = 'target to deploy (game, editor, tools)',
                            metavar = '<platform>')

        parser.add_argument('--max-revision',
                            help = 'Find a revision <= to this',
                            metavar = '<revision>')

        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        files_to_deploy = mapper = env.map_files()

        if hasattr(env, 'deploy_version_root'):
            mapper = mapper.to(env.deploy_version_root)
        else:
            mapper = mapper.to('.')

        if not hasattr(env, 'mode'):
            env.mode = 'binaries'

        if env.mode == 'binaries':
            log_notification("Deploying Binaries…")
            mapper = mapper.src(env.publish_binaries)
            mapper.load_set('binaries')

        if env.mode == 'version':
            log_notification("Deploying version…")
            src = env.publish_version
            if env.revision is None:
                revision = get_latest_available_revision(env, src, **vars(env))
                if revision is None:
                    return False
                env.revision = revision
            mapper = mapper.src(src)

        if env.mode == 'cook':
            log_error("Cook deployment not implemented yet...")
            return False

        mapper.glob("**").files()

        cl_number = p4_get_or_create_changelist('Deployment')
        if cl_number is None:
            return False

        files = list(files_to_deploy())
        dst_files = [dst for src, dst in files]
        p4_edit(cl_number, *dst_files)

        for src, dst in files:
            if not robocopy(src, dst):
                return False

        return True

