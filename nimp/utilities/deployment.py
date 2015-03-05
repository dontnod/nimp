# -*- coding: utf-8 -*-

from datetime import date

import os
import stat
import os.path
import tempfile;
import shutil
import stat
import glob
import fnmatch
import re
import contextlib
import pathlib

from nimp.utilities.perforce     import *
from nimp.utilities.file_mapper  import *

#---------------------------------------------------------------------------
def get_latest_available_revision(version_directory_format, start_revision, **kwargs):
    revisions                   = []
    kwargs['revision']          = '*'
    version_directory_format    = version_directory_format.replace('\\', '/')
    version_directories_glob    = version_directory_format.format(**kwargs)

    for version_directory in glob.glob(version_directories_glob):
        kwargs['revision'] = '([0-9]*)'
        version_directory  = version_directory.replace('\\', '/')
        version_regex      = version_directory_format.format(**kwargs)

        version_match = re.match(version_regex, version_directory)
        version_cl    = version_match.group(1)

        revisions.append(version_cl)

    revisions.sort(reverse=True)

    for revision in revisions:
        if start_revision is None or revision <= start_revision:
            return revision

    return None

#------------------------------------------------------------------------------
def upload_microsoft_symbols(context, paths):
    write_symbol_index = map_sources(lambda file: symbols_index.write(file + "\n"))

    with open("symbols_index.txt", "w") as symbols_index:
        for path in paths:
            write_symbol_index.frm(path)("**/*.pdb", "**/*.xdb")

    result = True
    if call_process(".",
                    [ "C:/Program Files (x86)/Windows Kits/8.1/Debuggers/x64/symstore.exe",
                      "add",
                      "/r", "/f",  "@symbols_index.txt",
                      "/s", context.symbol_server,
                      "/compress",
                      "/o",
                      "/t", "{0}_{1}_{2}".format(context.project, context.platform, context.configuration),
                      "/v", context.revision ]) != 0:
        result = False
        log_error("w00t ! An error occured while uploading symbols.")

    os.remove("symbols_index.txt")

    return result
