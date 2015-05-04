# -*- coding: utf-8 -*-

import os
import re
import subprocess
import sys
import threading
import time
import tempfile
import platform

from nimp.utilities.logging import *

if os.name is "nt":
    from nimp.utilities.windows_utilities import *

#-------------------------------------------------------------------------------
def _default_log_callback(line, default_log_function):
    default_log_function(line)

#-------------------------------------------------------------------------------
def _sanitize_command(command):
    # If we’re running under MSYS, leading slashes in command line arguments
    # will be treated as a path, so we need to escape them
    if os.environ.get('MSYSTEM') == 'MSYS':
        return [re.sub('^/', '//', x) for x in command]

    return command

#-------------------------------------------------------------------------------
def capture_process_output(directory, command, input = None):

    process = subprocess.Popen(_sanitize_command(command),
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
def call_process(directory, command, log_callback = _default_log_callback):
    log_verbose("Running {0} in directory {1}", command, directory)

    if os.name is "nt":
        ods_logger = OutputDebugStringLogger()

    process = subprocess.Popen(_sanitize_command(command),
                               cwd     = directory,
                               stdout  = subprocess.PIPE,
                               stderr  = subprocess.PIPE,
                               stdin   = None,
                               bufsize = 0)
    if os.name is "nt":
        ods_logger.attach(process.pid)
        ods_logger.start()

    def log_output(log_function, pipe):
        output_buffer = ""
        while process.poll() == None:
            try:
                for line in iter(pipe.readline, ''):
                    line  = line.decode("cp850")

                    if line == '':
                        break

                    line  = line.replace("{", "{{").replace("}", "}}")
                    line  = line.rstrip('\r\n')

                    log_callback(line, log_function)
            except ValueError:
                return

    log_thread_args = [ (log_verbose, process.stdout), (log_error, process.stderr) ]

    if os.name is "nt":
        log_thread_args += [(log_verbose, ods_logger.output)]

    log_threads     = [ threading.Thread(target = log_output, args = args) for args in log_thread_args ]

    for thread in log_threads:
        thread.start()

    process_return = process.wait()

    if os.name == "nt":
        ods_logger.stop()

    for thread in log_threads:
        thread.join()

    log_verbose("Program returned with code {0}", process_return)
    return process_return

