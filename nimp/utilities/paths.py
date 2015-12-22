# -*- coding: utf-8 -*-

import os
import os.path
import sys
import fnmatch
import glob

from nimp.utilities.logging import *
from nimp.utilities.system import *

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


def sanitize_path(path):
    if path is None:
        return None

    if is_windows() and not is_msys():
        if path[0:1] == '/' and path[1:2].isalpha() and path[2:3] == '/':
            return '%s:\\%s' % (path[1], path[3:].replace('/', '\\'))

    if os.sep is '\\':
        return path.replace('/', '\\')

    # elif os.sep is '/':
    return path.replace('\\', '/')


#-------------------------------------------------------------------------------
# This function is necessary because Python’s makedirs cannot create a
# directory such as "d:\data\foo/bar" because it’ll split it as "d:\data"
# and "foo/bar" then try to create a directory named "foo/bar".
def safe_makedirs(path):
    path = sanitize_path(path)

    try:
        os.makedirs(path)
    except FileExistsError:
        # Maybe someone else created the directory for us; if so, ignore error
        if os.path.exists(path):
            return
        raise

