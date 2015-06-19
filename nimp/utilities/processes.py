# -*- coding: utf-8 -*-

import os
import re
import subprocess
import sys
import threading
import time
import tempfile

from nimp.utilities.logging import *
from nimp.utilities.system import *
from nimp.utilities.windows_utilities import *

#-------------------------------------------------------------------------------
def _default_log_callback(line, default_log_function):
    default_log_function(line)

#-------------------------------------------------------------------------------
def _sanitize_command(command):
    # If we’re running under MSYS, leading slashes in command line arguments
    # will be treated as a path, so we need to escape them, except if the given
    # argument is indeed a file
    if is_msys():
        return [re.sub('^/', '//', x) for x in command]

    return command

#-------------------------------------------------------------------------------
def capture_process_output(directory, command, input = None):
    command = _sanitize_command(command)
    log_verbose(log_prefix() + "Running “{0}” in “{1}”", " ".join(command), directory)

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
    try:
        output, error = output.decode("utf-8"), error.decode("utf-8")
    except:
        output, error = output.decode("cp437"), error.decode("cp437")

    return process.wait(), output, error

#-------------------------------------------------------------------------------
def call_process(directory, command, stdout_callback = _default_log_callback,
                                     stderr_callback = None):
    command = _sanitize_command(command)
    log_verbose(log_prefix() + "Running “{0}” in “{1}”", " ".join(command), directory)

    debug_pipe = OutputDebugStringLogger()

    process = subprocess.Popen(command,
                               cwd     = directory,
                               stdout  = subprocess.PIPE,
                               stderr  = subprocess.PIPE,
                               stdin   = None,
                               bufsize = 0)
    debug_pipe.attach(process.pid)
    debug_pipe.start()

    def output_worker(user_callback, log_function, pipe):
        output_buffer = ""
        # FIXME: it would be better to use while process.poll() == None
        # here, but thread safety issues in Python < 3.4 prevent it.
        while process:
            try:
                for line in iter(pipe.readline, ''):
                    try:
                        line = line.decode("utf-8")
                    except:
                        line = line.decode("cp850")

                    if line == '':
                        break

                    line = line.replace("{", "{{").replace("}", "}}")
                    line = line.rstrip('\r\n')

                    user_callback(line, log_function)
            except ValueError:
                return

    if not stderr_callback:
        stderr_callback = stdout_callback

    log_thread_args = [ (stdout_callback, log_verbose, process.stdout),
                        (stderr_callback, log_error,   process.stderr),
                        (stderr_callback, log_verbose, debug_pipe.output)]
    log_threads = [ threading.Thread(target = output_worker, args = args) for args in log_thread_args ]

    for thread in log_threads:
        thread.start()

    process_return = process.wait()
    process = None

    debug_pipe.stop()

    for thread in log_threads:
        thread.join()

    log_verbose(log_prefix() + "Program “{0}” finished with exit code {1}", command[0], process_return)
    return process_return

