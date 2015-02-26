# -*- coding: utf-8 -*-

import os
import re
import subprocess
import sys
import threading
import time
import tempfile

from utilities.logging import *
from utilities.windows_utilities import *

#-------------------------------------------------------------------------------
def default_output_filter(line):
   return line

#-------------------------------------------------------------------------------
error_pattern    = "^\[NIMP_ERROR\](.*)\[/NIMP_ERROR\]$"
warning_pattern  = "^\[NIMP_WARNING\](.*)\[/NIMP_WARNING\]$"
error_regexp     = re.compile(error_pattern)
warning_regexp   = re.compile(warning_pattern)

#-------------------------------------------------------------------------------
def nimp_tag_output_filter(line):
    match_error = error_regexp.search(line)
    if match_error:
        error_string = match_error.group(1)
        log_error(error_string)
    else:
        match_warning = warning_regexp.search(line)
        if match_warning:
            warning_string = match_warning.group(1)
            log_warning(warning_string)
        else:
            log_verbose(line)
    return None


#-------------------------------------------------------------------------------
def capture_process_output(directory, command, input = None):
    process = subprocess.Popen(command,
                               cwd    = directory,
                               stdout = subprocess.PIPE,
                               stderr = subprocess.PIPE,
                               stdin  = subprocess.PIPE)
    if input is not None:
        input = input.encode("cp437")
    output, error = process.communicate(input)

    # Bonjour toi qui te tappe un bug parce que j'ai fait le connard et mis
    # l'encodage en dur.
    return process.wait(), output.decode("cp437"), error.decode("cp437")

#-------------------------------------------------------------------------------
def call_process(directory, command, output_filter = default_output_filter):
    log_verbose("Running {0} in directory {1}", command, directory)

    ods_logger = OutputDebugStringLogger()

    process = subprocess.Popen(command,
                               stdin                = None,
                               bufsize              = 0,
                               stdout               = subprocess.PIPE,
                               stderr               = subprocess.PIPE,
                               cwd                  = directory)

    ods_logger.log_process_output(process.pid)
    ods_logger.start()

    def log_output(log_function, pipe):
        output_buffer = ""
        while process.poll() == None:
            try:
                for  line in iter(pipe.readline, ''):
                    line  = line.decode("cp850")

                    if line == '':
                        break

                    line  = line.replace("{", "{{").replace("}", "}}")
                    line  = line.rstrip('\r\n')

                    if line == '':
                        continue

                    line  = output_filter(line)
                    log_function(line)
            except ValueError:
                return

    log_thread_args = [ (log_verbose, process.stdout), (log_error, process.stderr), (log_verbose, ods_logger.output) ]
    log_threads     = [ threading.Thread(target = log_output, args = args) for args in log_thread_args ]

    for thread in log_threads:
        thread.start()

    process_return = process.wait()

    ods_logger.stop()

    for thread in log_threads:
        thread.join()

    log_verbose("Program returned with code {0}", process_return)
    return process_return

#-------------------------------------------------------------------------------
def redirect_output(process):
    output = process.stdout.read()
    error  = process.stderr.read()

    if(error != ""):
        error = error[:-1]
        log_error(error)

    if(output != ""):
        output = output[:-1]
        log_verbose(output)

    return error != "" or output != ""

