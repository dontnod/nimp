# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import os.path
import urllib2
import urlparse

from nimp.utilities.files    import *
from nimp.utilities.logging  import *
from nimp.utilities.paths    import *

#-------------------------------------------------------------------------------
DOWNLOAD_BUFFER_SIZE = 1024

#-------------------------------------------------------------------------------
def download_file(file_url, destination_file_path):
    log_verbose("Downloading {0} => {1}...", file_url, destination_file_path)

    try:
        destination_file = open(destination_file_path, 'wb')
    except IOError as io_error:
        log_error("Can't open file {0} for writing : {1}", destination_file_path, io_error)
        return False

    try:
        url = urllib2.urlopen(file_url)
    except BaseException as url_error:
        log_error("Error while downloading {0} : {1}", file_url, url_error)
        return False

    meta_data           = url.info()
    content_length      = meta_data.getheaders("Content-Length")[0]
    file_size           = int(content_length)
    downloaded_size     = 0

    log_verbose("Download started")

    start_file_progress(file_size)

    try:
        while True:
            buffer = url.read(DOWNLOAD_BUFFER_SIZE)
            if not buffer:
                break

            downloaded_size += len(buffer)
            destination_file.write(buffer)
            update_progress(downloaded_size)

        end_progress()
        destination_file.close()
    except URLError as url_error:
        log_error("Error while downloading {0} : {1}", file_url, url_error)
        return False

    log_verbose("Download succeed")
    return True
