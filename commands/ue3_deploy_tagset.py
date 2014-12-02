# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
from datetime import date

import os
import stat
import os.path
import tempfile;
import shutil

from commands.command       import *
from utilities.compression  import *
from utilities.files        import *
from utilities.hashing      import *
from utilities.paths        import *
from utilities.processes    import *
from utilities.perforce     import *

COOKERSYNC_PATH  = "Binaries/Cookersync.exe"

#-------------------------------------------------------------------------------
class Ue3DeployTagsetCommand(Command):
    #---------------------------------------------------------------------------
    def __init__(self):
        Command.__init__(self, "ue3-deploy-tagset", "Deploy a previously zipped tagset locally")

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('source',
                            help    = 'Deploy this tagset',
                            metavar = '<source>',
                            type    = str)

        parser.add_argument('--workspace',
                            help    = 'Workspace to use to checkout versionned files',
                            metavar = '<workspace>',
                            type    = str)

        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        settings            = context.settings
        arguments           = context.arguments
        source_directory    = arguments.source

        result = True
        with PerforceTransaction(arguments.workspace, "Binaries checkout") as transaction:
            for root, directories, files in os.walk(source_directory, topdown=False):
                for file in files:
                    source_file     = os.path.join(root, file)
                    local_directory = os.path.relpath(root, source_directory)
                    local_file      = os.path.join(local_directory, file)

                    log_verbose("{0} => {1}", source_file, local_file)

                    if not os.path.exists(local_directory):
                        mkdir(local_directory)

                    transaction.add_file(local_file)

                    if os.path.exists(local_file):
                        os.chmod(local_file, stat.S_IWRITE)
                    shutil.copy(source_file, local_file)

        return result
