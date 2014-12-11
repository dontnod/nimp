# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import shutil

from commands.command       import *
from commands.vsbuild       import *

from config.system          import *

from utilities.files        import *
from utilities.hashing      import *
from utilities.paths        import *
from utilities.perforce     import *
from utilities.processes    import *

# TODO : Remove all non-versionned files from the repository

#-------------------------------------------------------------------------------
class CleanWorkspaceCommand(Command):

    def __init__(self):
        Command.__init__(self, 'clean-workspace', 'Cleans current workspace')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('--revert-only',
                            help    = 'Don\'t clean unversionned files, only revert pending changelists',
                            action  = "store_true",
                            default = False)
        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        settings = context.settings
        arguments = context.arguments

        return p4_clean_workspace()
