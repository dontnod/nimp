# -*- coding: utf-8 -*-

import os
import os.path
import shutil
import sys
import fnmatch
import glob

from nimp.utilities.logging import *

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
# This function is necessary because Python’s makedirs cannot create a
# directory such as "d:\data\foo/bar" because it’ll split it as "d:\data"
# and "foo/bar" then try to create a directory named "foo/bar".
def safe_makedirs(path):
    if os.sep is '\\':
        path = path.replace('/', '\\')
    elif os.sep is '/':
        path = path.replace('\\', '/')
    if not os.path.exists(path):
        os.makedirs(path)

