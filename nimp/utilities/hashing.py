# -*- coding: utf-8 -*-

import hashlib;
import os

from nimp.utilities.logging import *

#-------------------------------------------------------------------------------
def get_file_sha1(file_name):
    return get_file_hash(hashlib.sha1())

#-------------------------------------------------------------------------------
def get_file_md5(file_name):
    return get_file_hash(hashlib.md5())

#-------------------------------------------------------------------------------
def get_file_hash(hasher, file_name):
    file = open(file_name, "rb")
    while True:
        read_bytes = file.read(1024)
        if len(read_bytes) == 0:
            break
        hasher.update(read_bytes)
    return hasher.hexdigest()
