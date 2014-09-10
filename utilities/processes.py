# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
import os
import re
import subprocess
import sys
import threading
import time
import tempfile

from utilities.logging import *

#-------------------------------------------------------------------------------
# default_output_filter
def default_output_filter(line):
   return line

#-------------------------------------------------------------------------------
# crqr_tag_output_filter
error_pattern    = "^\[CRQR_ERROR\](.*)\[/CRQR_ERROR\]$"
warning_pattern  = "^\[CRQR_WARNING\](.*)\[/CRQR_WARNING\]$"
error_regexp     = re.compile(error_pattern)
warning_regexp   = re.compile(warning_pattern)

#-------------------------------------------------------------------------------
# crqr_tag_output_filter
def crqr_tag_output_filter(line):
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
# crqr_tag_output_filter
def convert_relative_paths(line):
    current_directory = os.getcwd()
    return line.replace("../../../../..", current_directory)

#-------------------------------------------------------------------------------
# call_process
def call_process(directory, command, output_filter = default_output_filter):
    stdout_file_name = tempfile.mktemp()
    stderr_file_name = tempfile.mktemp()

    stdout_file      = open(stdout_file_name, "wb")
    stderr_file      = open(stderr_file_name, "wb")

    log_verbose("Running {0} in directory {1}", command, directory)

    process          = subprocess.Popen(command,
                                        stdin   = None,
                                        stdout  = stdout_file,
                                        stderr  = stderr_file,
                                        cwd     = directory)
    process_ended    = threading.Event()
    process_ended.clear()

    def redirect_output():
        stdout_read_file = open(stdout_file_name, "rb")
        stderr_read_file = open(stderr_file_name, "rb")
        current_error   = ""
        current_output  = ""
        while True:
            output = stdout_read_file.readline()
            error  = stderr_read_file.readline()

            if(error != ""):
                current_error = current_error + error
                if "\n" in current_error:
                    current_error = current_error.strip("\n\r")
                    current_error = current_error.replace("{", "{{")
                    current_error = current_error.replace("}", "}}")
                    current_error = output_filter(current_error)
		    if current_error is not None:
		        log_error(current_error)
                    current_error = ""

            if(output != ""):
                current_output = current_output + output
                if "\n" in current_output:
                    current_output = current_output.strip("\n\r")
                    current_output = current_output.replace("{", "{{")
                    current_output = current_output.replace("}", "}}")
                    current_output = output_filter(current_output)
                    if current_output is not None:
		        log_verbose(current_output)
		    current_output = ""

            if output == "" and error == "" and process_ended.is_set():
                return

    redirect_output_thread = threading.Thread(target = redirect_output)
    redirect_output_thread.start()

    process_return = process.wait()
    process_ended.set()

    redirect_output_thread.join()

    stdout_file.close()
    stderr_file.close()

    os.remove(stdout_file_name)
    os.remove(stderr_file_name)

    if(process_return == 0):
        result = True
    else:
        log_verbose("Program returned with code {0}", process_return)
        result =  False

    return result

#-------------------------------------------------------------------------------
# redirect_output
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

