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
    stdout_file_name = tempfile.mktemp()
    stderr_file_name = tempfile.mktemp()

    stdout_file = open(stdout_file_name, "wb")
    stderr_file = open(stderr_file_name, "wb")

    log_verbose("Running {0} in directory {1}", command, directory)

    process = subprocess.Popen(command,
                               stdin   = None,
                               stdout  = stdout_file,
                               stderr  = stderr_file,
                               cwd     = directory)
    process_ended = threading.Event()
    process_ended.clear()

    def redirect_output():
        stdout_read_file = open(stdout_file_name, "rb")
        stderr_read_file = open(stderr_file_name, "rb")
        current_error   = ""
        current_output  = ""
        while True:
            output = stdout_read_file.readline()
            error  = stderr_read_file.readline()

            error  = error.decode("cp437")
            output = output.decode("cp437")
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

    if(process_return == 0):
        result = True
    else:
        log_verbose("Program returned with code {0}", process_return)
        result =  False

    return result

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

