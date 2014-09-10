# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# imports
#-------------------------------------------------------------------------------
from commands.command       import *

from configuration.system   import *

from utilities.logging      import *
from utilities.hashing      import *

#-------------------------------------------------------------------------------
# RunCmakeCommand
#-------------------------------------------------------------------------------
class Sha1Command(Command):

    def __init__(self):
        Command.__init__(self, "sha1", "Gets the sha1 of specified file(s)")

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):
        parser.add_argument('paths_to_hash',
                            metavar = 'FILE',
                            type    = str,
                            nargs   = "+")
        return True

    #---------------------------------------------------------------------------
    # run
    def run(self, context):
        arguments   = context.arguments
        paths_to_hash   = arguments.paths_to_hash
        for path_to_hash_it in paths_to_hash:
            if(os.path.isfile(path_to_hash_it)):
                print(get_file_sha1(path_to_hash_it))
            elif(os.path.isdir(path_to_hash_it)):
                for (directory_it, directories_it, files_it) in os.walk(path_to_hash_it):
                    for file_it in files_it:
                        file_path = os.path.join(directory_it, file_it)
                        print("[\"{0}\", \"{1}\"],".format(file_path, get_file_sha1(file_path)))

