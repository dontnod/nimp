# -*- coding: utf-8 -*-

import hashlib;
import os

from nimp.utilities.logging import *

#-------------------------------------------------------------------------------
def get_files_hash(pathes, file_path_format = None):
    result = []
    for path_it in pathes:
        log_verbose("Checking SHA1 in path {0}", path_it)
        if(os.path.isfile(path_it)):
            if(file_path_format is not None):
                formatted_file_path = file_path_format(path_it)
            result = result + [[ formatted_file_path, get_file_sha1(path_it) ]]
        elif(os.path.isdir(path_it)):
            for (directory_it, directories_it, files_it) in os.walk(path_it):
                for file_it in files_it:
                    file_path           = os.path.join(directory_it, file_it)
                    formatted_file_path = file_path
                    if(file_path_format is not None):
                        formatted_file_path = file_path_format(formatted_file_path)
                    result = result + [[ formatted_file_path, get_file_sha1(file_path) ]]
    return result

#-------------------------------------------------------------------------------
def get_file_sha1(file_name):
    file = open(file_name, "rb")
    hasher = hashlib.sha1()
    while True:
        read_bytes = file.read(1024)
        if len(read_bytes) == 0:
            break
        hasher.update(read_bytes)
    return hasher.hexdigest()
