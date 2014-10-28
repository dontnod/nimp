# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
from commands.command                   import *
from commands.vsbuild                   import *

from utilities.files                    import *
from utilities.hashing                  import *
from utilities.paths                    import *
from utilities.processes                import *

#-------------------------------------------------------------------------------
# Ue3BuildCommand
#-------------------------------------------------------------------------------
class GenerateVersionFileCommand(Command):

    def __init__(self):
        Command.__init__(self, 'generate-version-file', 'Generates a version file to be compiled with game')

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):

        return True

    #---------------------------------------------------------------------------
    # run
    def run(self, context):
        # Generate file
        return True
