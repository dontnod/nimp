# -*- coding: utf-8 -*-

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *
from nimp.utilities.deployment import *
from nimp.utilities.file_mapper import *

#-------------------------------------------------------------------------------
class GenerateTtsVoices(Command):
    def __init__(self):
        Command.__init__(self,
                         'generate-tts-voices',
                         'Generates tts voices from a JSON input')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('input',
                            help    = 'Json input file',
                            metavar = '<FILE>')

        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        files_to_deploy = mapper = env.map_files()
        if hasattr(env, 'deploy_version_root'):
            mapper = mapper.to(env.deploy_version_root)
        else:
            mapper = mapper.to('.')

        if not hasattr(env, 'mode') or env.mode == 'binaries':
            log_notification("Deploying Binaries…")
            mapper = mapper.src(env.publish_binaries)

        elif env.mode == 'version':
            src = env.publish_version
            if env.revision is None:
                revision = get_latest_available_revision(env, src, **vars(env))
                if revision is None:
                    return False
                env.revision = revision
            log_notification("Deploying version…")
            mapper = mapper.src(src)

        elif env.mode == 'cook':
            log_error("Not implemented yet...")
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

