# -*- coding: utf-8 -*-

import hashlib;
import os

from nimp.utilities.logging import *

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
