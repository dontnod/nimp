# -*- coding: utf-8 -*-

import os
import os.path
import shutil
import sys
import fnmatch
import glob

from nimp.utilities.logging  import *

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
