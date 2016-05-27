# -*- coding: utf-8 -*-
# Copyright (c) 2016 Dontnod Entertainment

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
''' System utilities (paths, processes) '''

import logging
import os
import platform
import subprocess
import sys
import threading
import time

import nimp.utilities.windows

def is_windows():
    ''' Return True if the runtime platform is Windows, including MSYS '''
    return is_msys() or platform.system() == 'Windows'

# Return True if the runtime platform is MSYS
def is_msys():
    ''' Returns True if the platform is msys. '''
    return platform.system()[0:7] == 'MSYS_NT'

def split_path(path):
    ''' Returns an array of path elements '''
    splitted_path = []
    while True:
        (path, folder) = os.path.split(path)

        if folder != "":
            splitted_path.insert(0, folder)
        else:
            if path != "":
                splitted_path.insert(0, path)
            break

    return splitted_path

def path_to_array(path):
    ''' Splits a path to an array '''
    directory, file = os.path.split(path)
    return path_to_array(directory) + [file] if directory  else [file]

def sanitize_path(path):
    ''' Perfmorms slash replacement to work on both msys and windows '''
    if path is None:
        return None

    if is_windows() and not is_msys():
        if path[0:1] == '/' and path[1:2].isalpha() and path[2:3] == '/':
            return '%s:\\%s' % (path[1], path[3:].replace('/', '\\'))

    if os.sep is '\\':
        return path.replace('/', '\\')

    # elif os.sep is '/':
    return path.replace('\\', '/')

def safe_makedirs(path):
    ''' This function is necessary because Python’s makedirs cannot create a
        directory such as d:\\data\\foo/bar because it’ll split it as "d:\\data"
        and "foo/bar" then try to create a directory named "foo/bar" '''
    path = sanitize_path(path)

    try:
        os.makedirs(path)
    except FileExistsError:
        # Maybe someone else created the directory for us; if so, ignore error
        if os.path.exists(path):
            return
        raise

def capture_process_output(directory, command, stdin = None, encoding = 'utf-8'):
    ''' Returns a 3-uple containing return code, stdout and stderr of the given
        command '''
    command = _sanitize_command(command)
    logging.debug("Running “%s” in “%s”", " ".join(command), os.path.abspath(directory))
    process = subprocess.Popen(command,
                               cwd     = directory,
                               stdout  = subprocess.PIPE,
                               stderr  = subprocess.PIPE,
                               stdin   = subprocess.PIPE,
                               bufsize = 1)
    output, error = process.communicate(stdin.encode(encoding) if stdin else None)

    return process.wait(), output.decode(encoding), error.decode(encoding)

def call_process(directory, command, heartbeat = 0):
    ''' Calls a process redirecting its output to nimp's output '''
    command = _sanitize_command(command)
    logging.debug("Running “%s” in “%s”", " ".join(command), os.path.abspath(directory))

    if is_windows():
        nimp.utilities.windows.disable_win32_dialogs()
        debug_pipe = nimp.utilities.windows.OutputDebugStringLogger()

    # The bufsize = 1 is important; if we don’t bufferise the
    # output, we’re going to make the callee lag a lot.
    process = subprocess.Popen(command,
                               cwd     = directory,
                               stdout  = subprocess.PIPE,
                               stderr  = subprocess.PIPE,
                               stdin   = None,
                               bufsize = 1)
    if is_windows():
        debug_pipe.attach(process.pid)
        debug_pipe.start()

    def _heartbeat_worker(heartbeat):
        last_time = time.monotonic()
        while process:
            if heartbeat > 0 and time.monotonic() > last_time + heartbeat:
                logging.info("Keepalive for %s", command[0])
                last_time += heartbeat
            time.sleep(0.050)

    def _output_worker(in_pipe, out_pipe):
        # FIXME: it would be better to use while process.poll() == None
        # here, but thread safety issues in Python < 3.4 prevent it.
        while process:
            try:
                for line in iter(in_pipe.readline, ''):
                    try:
                        line = line.decode("utf-8")
                    except UnicodeError:
                        line = line.decode("cp850")

                    if line == '':
                        break

                    out_pipe.write(line)

                # Sleep for 10 milliseconds if there was no data,
                # or we’ll hog the CPU.
                time.sleep(0.010)

            except ValueError:
                return

    log_thread_args = [ (process.stdout, sys.stdout),
                        (process.stderr, sys.stderr) ]
    if is_windows():
        log_thread_args += [ (debug_pipe.output, sys.stdout) ]

    worker_threads = [ threading.Thread(target = _output_worker, args = args) for args in log_thread_args ]
    # Send keepalive to stderr if requested
    if heartbeat > 0:
        worker_threads += [ threading.Thread(target = _heartbeat_worker, args = (heartbeat, )) ]

    for thread in worker_threads:
        thread.start()

    try:
        process_return = process.wait()
    finally:
        process = None
        if is_windows():
            debug_pipe.stop()
        for thread in worker_threads:
            thread.join()

    if process_return == 0:
        log = logging.debug
    else:
        log = logging.error
    log("Program “%s” finished with exit code %s", command[0], process_return)

    return process_return

def _sanitize_command(command):
    new_command = []
    for it in command:
        # If we’re running under MSYS, leading slashes in command line arguments
        # will be treated as a path, so we need to escape them, except if the given
        # argument is indeed a file.
        if it[0:1] == '/':
            if is_msys():
                # If the argument starts with /, we may wish to rewrite it
                if it[1:2].isalpha() and it[2:3] == '/':
                    # Stuff like /c/... looks like a path with a drive letter, keep it that way
                    # but /c is most probably a flag, so that one needs to be escaped
                    pass
                elif len(it) > 5 and (os.path.isfile(it) or os.path.isdir(it)):
                    pass
                else:
                    it = '/' + it
        new_command.append(it)
    return new_command

