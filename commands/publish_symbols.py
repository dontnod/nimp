# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
from datetime import date

import os
import fnmatch
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

SYMBOLS_FILE_PATTERNS    = [ "*.map", "*.pdb" ]

#-------------------------------------------------------------------------------
class PublishSymbols(Command):
    #---------------------------------------------------------------------------
    def __init__(self):
        Command.__init__(self, "publish-symbols", "Publishes symbols to shared directory")

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        parser.add_argument('platform',
                            help    = 'Platform to publish binaries from',
                            metavar = '<platform>')

        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        settings            = context.settings
        arguments           = context.arguments

        head_cl             = p4_get_last_synced_changelist()
        platform            = arguments.platform

        source_format       = settings.symbols_source
        destination_format  = settings.symbols_destination
        source              = source_format.format(platform = platform)
        destination         = destination_format.format(platform = platform, change_list = head_cl)

        mkdir(destination)

        for pattern in SYMBOLS_FILE_PATTERNS:
            for root, directories, filenames in os.walk(source):
                for filename in fnmatch.filter(filenames, pattern):
                    symbol_path           = os.path.join(root, filename)
                    relative_destination  = os.path.relpath(symbol_path, source)
                    symbol_destination    = os.path.join(destination, relative_destination)
                    destination_directory = os.path.dirname(symbol_destination)

                    if not os.path.isdir(destination_directory):
                        mkdir(destination_directory)

                    try:
                        shutil.copy(symbol_path, symbol_destination)
                    except Exception as ex:
                        log_warning("Unable to copy {0} : {1}", symbol_path, ex)

        return True