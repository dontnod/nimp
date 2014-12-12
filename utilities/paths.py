# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# imports
#-------------------------------------------------------------------------------
import os
import os.path
import shutil
import sys
import fnmatch

from utilities.logging  import *
from config.system      import *

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
def get_matching_files(path, pattern = '*'):
    """ Returns an array containing only path if path is a file, or all files
        matching pattern in path and his subdirectory if path is a directory.
    """
    if os.path.isfile(path):
        return [path]
    elif os.path.isdir(path):
        result = []
        for root, directories, files in os.walk(path):
            for file in files:
                if fnmatch.fnmatch(file, pattern):
                    result.append(os.path.join(root, file))
        return result
    else:
        log_error("Can't find file or directory {0}", path)
        return None

#-------------------------------------------------------------------------------
def get_matching_subdirectories(path, pattern = '*'):
    """ Returns an array containing only path if path is a file, or all files
        matching pattern in path and his subdirectory if path is a directory.
    """

    if os.path.isdir(path):
        result = []
        for root, directories, files in os.walk(path):
            for directory in directories:
                if fnmatch.fnmatch(directory, pattern):
                    result.append(os.path.join(root, directory))
        return result
    else:
        log_error("Can't find directory {0}", path)
        return None

#-------------------------------------------------------------------------------
def get_main_path():
    try:
        return os.path.abspath(sys.modules['__main__'].__file__)
    except:
        return sys.executable

#-------------------------------------------------------------------------------
def get_python_path():
    os_module_path          = os.path.dirname(os.__file__)
    python_executable_path  = os.path.normpath(os.path.join(os_module_path, "../python"))
    return executable_name(python_executable_path)
