# -*- coding: utf-8 -*-

import os
import os.path
import shutil
import sys
import fnmatch
import glob

from utilities.logging  import *

#-------------------------------------------------------------------------------
def check_exists(path):
    log_verbose("Checking path {0} consistency", path)
    if(not os.path.exists(path)):
        log_error("Can't find path {0}", path)
        return False;
    return True

#-------------------------------------------------------------------------------
def get_extension(path):
    return os.path.splitext(path)[1]

#-------------------------------------------------------------------------------
def get_path_without_extension(path):
    return os.path.splitext(path)[0]

#-------------------------------------------------------------------------------
def get_file_name_without_extension(path):
    base_name = os.path.basename(path)
    return os.path.splitext(base_name)[0]

#-------------------------------------------------------------------------------
def mkdir(directory_path):
    if os.path.exists(directory_path):
        log_verbose("Directory {0} already exists.", directory_path)
        return
    log_verbose("Directory {0} created.", directory_path)
    os.makedirs(directory_path)

#-------------------------------------------------------------------------------
def rmdir(directory_path):
    shit_happened = [False]
    def on_error(function, path, excinfo):
        shit_happened[0] = True

    if os.path.exists(directory_path):
        shutil.rmtree(directory_path, False, on_error)
    return not shit_happened[0]

#-------------------------------------------------------------------------------
def get_settings_directory():
    return os.getenv(USER_DIRECTORY_ENVIRONMENT_VARIABLE)

#-------------------------------------------------------------------------------
def split_path(path):
    splitted_path = []
    while True:
        (path, folder) = os.path.split(path)

        if folder != "":
            splitted_path.insert(0, folder)
        else:
            if path != "":
                splitted_path.insert(0, path)
            break

    return splitted_path

#-------------------------------------------------------------------------------
def list_files(source, recursive):
    """ Extended list files method.
        Source can either be a file, a directory or a glob expression.
    """
    if os.path.exists(source):
        if os.path.isfile(source) and os.path.exists(source):
            yield source
        elif os.path.isdir(source) and recursive:
            for root, directories, files in os.walk(source):
                for file in files:
                    yield os.path.join(root, file)
        elif os.path.isdir(source) and not recursive:
            for child in os.listdir(source):
                if os.path.isfile(child):
                    yield child
        else:
            assert(false)
    else:
        for glob_source in glob.glob(source):
            for file in list_files(glob_source, recursive):
                yield file

#-------------------------------------------------------------------------------
def filter_matching_files(paths, include = ['*'], exclude = []):
    """ Filters files matching one of the include pattern and none of exclude
        patterns.
        The filename of each path will be extracted before matching.
    """
    for path in paths:
        match = False
        for pattern in include:
            if fnmatch.fnmatch(os.path.basename(path), pattern):
                match = True
                break
        for pattern in exclude:
            if fnmatch.fnmatch(os.path.basename(path), pattern):
                match = False
                break
        if match:
            yield path

#-------------------------------------------------------------------------------
def list_files_matching(source, include = ['*'], exclude = [], recursive = True):
    """ List files in source, returns files wich name matches all of include
        patterns and none of exclude patterns. source can either be a file,
        a directory or a glob expression.
        The filename of each path will be extracted before matching.
    """
    all_files = list_files(source, recursive)
    return filter_matching_files(all_files, include, exclude)
