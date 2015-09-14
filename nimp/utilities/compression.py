# -*- coding: utf-8 -*-

import os.path

from decimal import *
import tarfile
import zipfile

from nimp.utilities.logging import *
from nimp.utilities.paths import *

#-------------------------------------------------------------------------------
TAR_FILE = 1
ZIP_FILE = 2

DECOMPRESS_BAR_TEMPLATE = "[{filled_chars}{empty_chars}] {step_name}"
DECOMLPRESS_BAR_WIDTH   = 15
MAXIMUM_STEP_NAME_WIDTH = 57

#-------------------------------------------------------------------------------
def extract(archive_file_name, destination_directory, archive_type = None, before_decompress_file_callback = None):
    log_verbose("Determining type of archive {0}", archive_file_name)
    if(archive_type is None):
        first_extension =  os.path.splitext(archive_file_name)[1]
        file_name_without_extension = os.path.splitext(archive_file_name)[0]
        second_extension = os.path.splitext(file_name_without_extension)[1]
        if(first_extension == ".zip"):
            archive_type = ZIP_FILE
            log_verbose("Archive must be a zip")
        elif(first_extension == ".tar"):
            log_verbose("Archive must be an uncompressed tarfile")
            archive_type = TAR_FILE
        elif( ( first_extension == ".gz" or first_extension == ".bz2") and ( second_extension == ".tar" ) ):
            log_verbose("Archive must be a compressed tarfile")
            archive_type = TAR_FILE
        else:
            log_error("Unable to determine archive type of {0} based on it's name. Please specify it", archive_file_name)
            return False
    if(archive_type == TAR_FILE):
        return _decompress_tar(archive_file_name, destination_directory)
    elif(archive_type == ZIP_FILE):
        return _decompress_zip(archive_file_name, destination_directory)
    else:
        log_error("Bad archive type. Please specify TAR_FILE or ZIP_FILE")

    return False

#-------------------------------------------------------------------------------
def _decompress_tar(file_name, destination_directory, before_decompress_file_callback = None):
    log_verbose("Decompressing {0} in {1}", file_name, destination_directory)
    try:
        tar_file = tarfile.open(file_name)
        file_names = tar_file.getnames()
        current_file = 0

        start_progress(len(file_names),
                       template = DECOMPRESS_BAR_TEMPLATE,
                       width    = DECOMLPRESS_BAR_WIDTH)

        for value_it in tar_file.pax_headers:
            print(value_it[0] + "=>" + value_it[1])
        for file_name_it in file_names:
            _extract_file(tar_file, destination_directory, file_name_it, current_file)
            current_file += 1
        end_progress()

    except tarfile.TarError as tar_error:
        log_error("Error while opening tarfile {0}: {1}", file_name, tar_error)
        return False
    except IOError as io_error:
        log_error("Unable to open tarfile {0}: {1}", file_name, io_error)
        return False

    log_verbose("Decompression succeed")
    return True

#-------------------------------------------------------------------------------
def _decompress_zip(file_name, destination_directory, before_decompress_file_callback = None):
    log_verbose("Decompressing {0} in {1}", file_name, destination_directory)
    try:
        zip_file = zipfile.ZipFile(file_name, "r")
        file_names = zip_file.namelist()
        current_file = 0

        start_progress(len(file_names),
                       template = DECOMPRESS_BAR_TEMPLATE,
                       width    = DECOMLPRESS_BAR_WIDTH)

        for file_name_it in file_names:
            _extract_file(zip_file, destination_directory, file_name_it, current_file)
            current_file += 1
        end_progress()

    except zipfile.BadZipfile as zip_error:
        log_error("Error while opening zip {0}: {1}", file_name, zip_error)
        return False
    except IOError as io_error:
        log_error("Unable to open zip {0}: {1}", file_name, io_error)
        return False

    log_verbose("Decompression succeed")
    return True

#-------------------------------------------------------------------------------
def _extract_file(archive, destination_directory, file_name, file_index, before_decompress_file_callback = None):
    step_name = file_name
    step_name_size = len(step_name)

    if step_name_size > MAXIMUM_STEP_NAME_WIDTH:
        step_name = "..." + step_name[step_name_size - MAXIMUM_STEP_NAME_WIDTH:step_name_size]

    update_progress(file_index, step_name)

    if before_decompress_file_callback is not None:
        before_decompress_file_callback(destination_directory, file_name)

    archive.extract(file_name, destination_directory)
    update_progress(file_index + 1, step_name)
