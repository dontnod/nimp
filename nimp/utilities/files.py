# -*- coding: utf-8 -*-

import os.path
import re
import shutil
import stat
import string
import tempfile;
import time
import fnmatch
import glob

from nimp.utilities.logging    import *
from nimp.utilities.units      import *

#-------------------------------------------------------------------------------
READ_BUFFER_SIZE = 1024*1024*3

#-------------------------------------------------------------------------------
def copy_file(source_path, destination_path):
    if(not os.path.exists(source_path)):
        log_error("File {0} doesn't exist", source_path)
        return False

    input_file = open_readable(source_path)
    if input_file is None:
        return False

    output_file = open_writable(destination_path)
    if output_file is None:
        return False

    file_size = os.path.getsize(source_path)
    total_read_bytes    = 0

    log_notification("{0} => {1}", source_path, destination_path)
    start_file_progress(file_size)

    while(True):
        buffer = input_file.read(READ_BUFFER_SIZE)
        if(buffer is None or len(buffer) == 0):
            break

        total_read_bytes = total_read_bytes + len(buffer)
        output_file.write(buffer)

        update_progress(total_read_bytes)

    end_progress()

    input_file.close()
    output_file.close()
    shutil.copymode(source_path, destination_path)

    return True

#-------------------------------------------------------------------------------
def copy_files(file_list):
    def empty_format(value, width = 7, alignement = ">"):
        return ""

    source_destination_pairs    = file_list.items()
    total_files                 = len(source_destination_pairs)
    current_file                = 0
    start_progress(total_files, speed_formatter = empty_format)

    for (source, destination) in source_destination_pairs:
        source                  = os.path.abspath(source)
        destination             = os.path.abspath(destination)
        destination_directory   = os.path.dirname(destination)

        if not os.path.exists(destination_directory):
            os.makedirs(destination_directory)

        shutil.copyfile(source, destination)
        shutil.copymode(source, destination)
        current_file = current_file + 1
        update_progress(current_file)
    end_progress()

    return True

#-----------------------------------------------------------------------------
def set_executable(file_list):
    for file in file_list:
        os.chmod(file, stat.S_IXGRP | stat.S_IRGRP | stat.S_IXUSR | stat.S_IRUSR)

    return True

#-----------------------------------------------------------------------------
def open_readable(file_path):
    log_verbose("Opening {0} for reading", file_path)
    try:
        file = open(file_path, "rb")
    except IOError as io_error:
        log_error("Unable to open file {0} for reading : {1}", file_path, io_error)
        return None
    return file

#-----------------------------------------------------------------------------
def read_file_content(file_path):
    file_to_read = open_readable(file_path)
    if file_to_read is None:
        return None
    result = file_to_read.read()
    file_to_read.close()
    return result

#-----------------------------------------------------------------------------
def open_writable(file_path):
    log_verbose("Opening {0} for writing", file_path)
    try:
        file = open(file_path, "wb")
    except IOError as io_error:
        log_error("Unable to open file {0} for writing : {1}", file_path, io_error)
        return None
    return file

#-------------------------------------------------------------------------------
def open_temp_file(suffix = ""):
    temporary_file_name = os.tempnam()
    temporary_file_name = "{0}_{1}".format(temporary_file_name, suffix)
    return open_writable(temporary_file_name);

#-------------------------------------------------------------------------------
def write_file_content(file_path, content, encoding = "utf8"):
    file_to_read = open_writable(file_path)
    if file_to_read is None:
        return False
    file_to_read.write(content.encode(encoding))
    file_to_read.close()
    return True

#-------------------------------------------------------------------------------
def start_file_progress(file_size):

    def total_formatter(value):
        return format_octet(value, width = None, alignement = "<")

    start_progress(total                 = file_size,
                   position_formatter    = format_octet,
                   speed_formatter       = format_octet_per_second,
                   total_formatter       = total_formatter)

#-------------------------------------------------------------------------------
def is_binary(file_path):
    text_characters = "".join(map(chr, range(32, 127)) + list("\n\r\t\b"))
    _null_trans     = string.maketrans("", "")

    file = open_readable(file_path)

    if file is None:
        return None

    block = file.read(512)

    if "\0" in block:
        return True

    if not block:
        return False

    translated_block = block.translate(_null_trans, text_characters)

    if len(translated_block)/len(block) < 0.30:
        return False

    return True
