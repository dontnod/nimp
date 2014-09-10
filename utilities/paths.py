# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# imports
#-------------------------------------------------------------------------------
import os
import os.path
import shutil
import sys

from utilities.logging      import *
from configuration.system   import *

#-------------------------------------------------------------------------------
# check_path_exists
def check_exists(path):
    log_verbose("Checking path {0} consistency", path)
    if(not os.path.exists(path)):
        log_error("Can't find path {0}", path)
        return False;
    return True

#-------------------------------------------------------------------------------
# get_extension
def get_extension(path):
    return os.path.splitext(path)[1]

#-------------------------------------------------------------------------------
# get_path_without_extension
def get_path_without_extension(path):
    return os.path.splitext(path)[0]

#-------------------------------------------------------------------------------
# mkdir
def mkdir(directory_path):
    if os.path.exists(directory_path):
        log_verbose("Directory {0} already exists.", directory_path)
        return
    log_verbose("Directory {0} created.", directory_path)
    os.makedirs(directory_path)

#-------------------------------------------------------------------------------
# rmdir
def rmdir(directory_path):
    shit_happened = [False]
    def on_error(function, path, excinfo):
        shit_happened[0] = True

    if os.path.exists(directory_path):
        shutil.rmtree(directory_path, False, on_error)
    return not shit_happened[0]

#-------------------------------------------------------------------------------
# get_settings_directory
def get_settings_directory():
    return os.getenv(USER_DIRECTORY_ENVIRONMENT_VARIABLE)

#-------------------------------------------------------------------------------
# get_settings_directory
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
# get_main_path
def get_main_path():
    try:
        return os.path.abspath(sys.modules['__main__'].__file__)
    except:
        return sys.executable

#-------------------------------------------------------------------------------
# get_python_path
def get_python_path():
    os_module_path          = os.path.dirname(os.__file__)
    python_executable_path  = os.path.normpath(os.path.join(os_module_path, "../python"))
    return executable_name(python_executable_path)
