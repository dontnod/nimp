# -*- coding: utf-8 -*-

from datetime import date

import os
import stat
import os.path
import tempfile;
import stat
import glob
import fnmatch
import re
import contextlib

from nimp.utilities.perforce import *
from nimp.utilities.file_mapper import *
from nimp.utilities.system import *

#------------------------------------------------------------------------------
def upload_symbols(env, symbols):

    result = True

    if env.is_microsoft_platform:
        index_file = "symbols_index.txt"
        with open(index_file, "w") as symbols_index:
            for src, dest in symbols:
                symbols_index.write(src + "\n")

        store_root = sanitize_path(env.format(env.publish_symbols))
        transaction_comment = "{0}_{1}_{2}_{3}".format(env.project, env.platform, env.configuration, env.revision)
        if call_process(".",
                        [ "C:/Program Files (x86)/Windows Kits/8.1/Debuggers/x64/symstore.exe",
                          "add",
                          "/compress",
                          "/r", # Recursive
                          "/f", "@" + index_file,
                          "/s", store_root,
                          "/o", # Verbose output
                          "/t", env.project, # Product name
                          "/c", transaction_comment,
                          "/v", env.revision ]) != 0:
            log_error(log_prefix() + "Oops! An error occurred while uploading symbols.")
            # Do not remove symbol index; keep it for later debugging
            return False

        os.remove(index_file)

    return True

#------------------------------------------------------------------------------
def get_symbol_transactions(symsrv):
    server_txt_path =  os.path.join(symsrv, "000Admin", "server.txt")
    if not os.path.exists(server_txt_path):
        log_error("Unable to find the file {0}, aborting.", server_txt_path)
        return None
    line_re = re.compile("^(?P<id>\d*),"
                         "(?P<operation>(add|del)),"
                         "(?P<type>(file|ptr)),"
                         "(?P<creation_date>\d{2}\/\d{2}\/\d{4}),"
                         "(?P<creation_time>\d{2}:\d{2}:\d{2}),"
                         "\"(?P<product_name>[^\"]*)\","
                         "\"(?P<version>[^\"]*)\","
                         "\"(?P<comment>[^\"]*)\",$")
    transaction_infos = []
    with open(server_txt_path, "r") as server_txt:
        for line in server_txt.readlines():
            match = line_re.match(line)
            if not match:
                log_error("{0} is not recognized as a server.txt transaction entry", line)
                return None
            transaction_infos += [match.groupdict()]
    return transaction_infos

#------------------------------------------------------------------------------
def delete_symbol_transaction(symsrv, transaction_id):
    if call_process(".",
                    [ "C:/Program Files (x86)/Windows Kits/8.1/Debuggers/x64/symstore.exe", "del", "/i", transaction_id, "/s", symsrv]) != 0:
        log_error("Oops! An error occurred while deleting symbols.")
        return False
    return True

