# -*- coding: utf-8 -*-
# Copyright (c) 2014-2019 Dontnod Entertainment

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

'''Process-related system utilities'''

from __future__ import annotations

import ctypes
import locale
import logging
import os
import os.path
import struct
import subprocess
import threading
import time
from enum import Enum
from typing import TYPE_CHECKING

import nimp.sys.platform

if TYPE_CHECKING:
    from typing import Callable


class ProcessOutputStream(Enum):
    """
    process output stream identifiers
    """

    STDOUT = 1
    STDERR = 2
    STDDBG = 3


def call(
    command,
    cwd='.',
    heartbeat=0,
    stdin=None,
    encoding='utf-8',
    capture_output: bool | Callable[[ProcessOutputStream, str], None] = False,
    capture_debug=False,
    hide_output=False,
    dry_run=False,
    timeout=None,
    **popen_kwargs,
):
    '''Calls a process redirecting its output to nimp's output'''
    command = _sanitize_command(command)

    if not hide_output:
        logging.info('%s "%s" in "%s"', '[DRY-RUN]' if dry_run else 'Running', command, os.path.abspath(cwd))
    if dry_run:
        if capture_output is True:
            return 0, '', ''
        else:
            return 0

    if capture_debug and not hide_output and nimp.sys.platform.is_windows():
        _disable_win32_dialogs()
        debug_pipe = _OutputDebugStringLogger()
    else:
        debug_pipe = None

    for reserved_popen_kwargs in [
        'stdout',
        'stderr',
        'stdin',
        'bufsize',
    ]:
        if reserved_popen_kwargs in popen_kwargs:
            value = popen_kwargs.pop(reserved_popen_kwargs)
            logging.debug("Ignoring reserved subprocess.Popen kwarg '%s=%s'", reserved_popen_kwargs, value)

    # The bufsize = -1 is important; if we don’t bufferise the output, we’re
    # going to make the callee lag a lot. In Python 3.3.1 this is now the
    # default behaviour, but it used to default to 0.
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            bufsize=-1,
        )
    except FileNotFoundError as ex:
        logging.error(ex)
        return 1

    if debug_pipe:
        debug_pipe.attach(process.pid)
        debug_pipe.start()

    # FIXME: put all this in a class instead!
    all_pipes = {
        ProcessOutputStream.STDOUT: process.stdout,
        ProcessOutputStream.STDERR: process.stderr,
        ProcessOutputStream.STDDBG: debug_pipe.output if debug_pipe else None,
    }

    all_captures: dict[ProcessOutputStream, list[str]] = {
        ProcessOutputStream.STDOUT: [],
        ProcessOutputStream.STDERR: [],
    }

    def _capture_output_default(stream: ProcessOutputStream, value: str):
        if (capture_array := all_captures.get(stream)) is not None:
            capture_array.append(value)

    capture_processor: Callable[[ProcessOutputStream, str], None] | None = None
    if capture_output is True:
        capture_processor = _capture_output_default
    elif callable(capture_output):
        capture_processor = capture_output

    debug_info = [False]

    def _heartbeat_worker(heartbeat):
        last_time = time.monotonic()
        while process is not None:
            if heartbeat > 0 and time.monotonic() > last_time + heartbeat:
                logging.info("Keepalive for %s", command[0])
                last_time += heartbeat
            time.sleep(0.050)

    def _input_worker(in_pipe, data):
        in_pipe.write(data)
        in_pipe.close()

    def _output_worker(index: ProcessOutputStream, decoding_format) -> None:
        in_pipe = all_pipes[index]
        if in_pipe is None:
            return
        force_ascii = locale.getpreferredencoding().lower() != 'utf-8'
        while process is not None:
            logger = logging.getLogger('child_processes')
            # Try to decode as UTF-8 with BOM first; if it fails, try CP850 on
            # Windows, or UTF-8 with BOM and error substitution elsewhere. If
            # it fails again, try CP850 with error substitution.
            encodings = [
                (decoding_format, 'strict'),
                ('ascii', 'backslashreplace') if force_ascii else ('utf-8-sig', 'strict'),
                ('cp850', 'strict') if nimp.sys.platform.is_windows() else ('utf-8-sig', 'replace'),
                ('cp850', 'replace'),
            ]
            for data in iter(in_pipe.readline, b''):
                for encoding, errors in encodings:
                    try:
                        line = data.decode(encoding, errors=errors)
                        break
                    except UnicodeError:
                        pass

                if capture_processor is not None:
                    capture_processor(index, line)

                # Stop reading data from stdout if data has arrived on OutputDebugString
                if index == 2:
                    debug_info[0] = True
                elif index == 0 and debug_info[0]:
                    logging.info('Stopping stdout monitoring (OutputDebugString is active)')
                    all_pipes[ProcessOutputStream.STDOUT].close()
                    return

                if not hide_output:
                    logger.info(line.strip('\n').strip('\r'))

            # Sleep for 10 milliseconds if there was no data,
            # or we’ll hog the CPU.
            time.sleep(0.010)

    # Default threads
    all_workers = [
        threading.Thread(target=_output_worker, args=(i, encoding))
        for i in [
            ProcessOutputStream.STDOUT,
            ProcessOutputStream.STDERR,
            ProcessOutputStream.STDDBG,
        ]
    ]

    # Thread to feed stdin data if necessary
    if stdin is not None:
        all_workers.append(threading.Thread(target=_input_worker, args=(process.stdin, stdin.encode(encoding))))

    # Send keepalive to stderr if requested
    if heartbeat > 0:
        all_workers.append(threading.Thread(target=_heartbeat_worker, args=(heartbeat,)))

    for thread in all_workers:
        thread.start()

    try:
        exit_code = process.wait(timeout)
    finally:
        process = None
        # For some reason, must be done _before_ threads are joined, or
        # we get stuck waiting for something!
        if debug_pipe:
            debug_pipe.stop()
            debug_pipe = None
        for thread in all_workers:
            thread.join()

    if not hide_output:
        logging.info('Finished with exit code %d (0x%08x)', exit_code, exit_code)

    if capture_output is True:
        return (
            exit_code,
            ''.join(all_captures[ProcessOutputStream.STDOUT]),
            ''.join(all_captures[ProcessOutputStream.STDERR]),
        )
    return exit_code


def _sanitize_command(command):
    new_command = []
    for it in command:
        # If we’re running under MSYS, leading slashes in command line arguments
        # will be treated as a path, so we need to escape them, except if the given
        # argument is indeed a file.
        if it[0:1] == '/':
            if nimp.sys.platform.is_msys():
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


if nimp.sys.platform.is_windows():
    _KERNEL32 = ctypes.windll.kernel32 if hasattr(ctypes, 'windll') else None  # pylint: disable = invalid-name
    _KERNEL32.MapViewOfFile.restype = ctypes.c_void_p
    _KERNEL32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]

    # Should be c_void_p(-1).value but doesn’t work
    INVALID_HANDLE_VALUE = -1  # pylint: disable = invalid-name

    WAIT_OBJECT_0 = 0x00000000  # pylint: disable = invalid-name
    WAIT_OBJECT_1 = 0x00000001  # pylint: disable = invalid-name
    INFINITE = 0xFFFFFFFF  # pylint: disable = invalid-name

    PAGE_READWRITE = 0x4  # pylint: disable = invalid-name

    FILE_MAP_READ = 0x0004  # pylint: disable = invalid-name

    SEM_FAILCRITICALERRORS = 0x0001  # pylint: disable = invalid-name
    SEM_NOGPFAULTERRORBOX = 0x0002  # pylint: disable = invalid-name
    SEM_NOOPENFILEERRORBOX = 0x8000  # pylint: disable = invalid-name

    PROCESS_QUERY_INFORMATION = 0x0400  # pylint: disable = invalid-name
    PROCESS_SYNCHRONIZE = 0x00100000  # pylint: disable = invalid-name

    def _disable_win32_dialogs():
        '''Disable "Entry Point Not Found" and "Application Error" dialogs for
        child processes'''

        _KERNEL32.SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX | SEM_NOOPENFILEERRORBOX)

    class _OutputDebugStringLogger(threading.Thread):
        '''Get output debug string from a process and writes it to a pipe'''

        def __init__(self):
            super().__init__()

            fd_in, fd_out = os.pipe()
            self.output = os.fdopen(fd_in, 'rb')
            self._pipe_in = os.fdopen(fd_out, 'wb')

            self._buffer_ev = _KERNEL32.CreateEventW(None, 0, 0, 'DBWIN_BUFFER_READY')
            self._data_ev = _KERNEL32.CreateEventW(None, 0, 0, 'DBWIN_DATA_READY')
            self._stop_ev = _KERNEL32.CreateEventW(None, 0, 0, None)
            self._bufsize = 4096

            self._mapping = _KERNEL32.CreateFileMappingW(
                INVALID_HANDLE_VALUE, None, PAGE_READWRITE, 0, self._bufsize, 'DBWIN_BUFFER'
            )

            self._buffer = _KERNEL32.MapViewOfFile(self._mapping, FILE_MAP_READ, 0, 0, self._bufsize)
            self._pid = None

        @staticmethod
        def _pid_to_winpid(pid):
            # In case we’re running in MSYS2 Python, the PID we got is actually an
            # internal MSYS2 PID, and the PID we want to watch is actually the WINPID,
            # which we retrieve in /proc
            try:
                return int(open("/proc/%d/winpid" % (pid,)).read(10))
            # pylint: disable=broad-except
            except Exception:
                return pid

        def attach(self, pid):
            '''Sets the process pid from which to capture output debug string'''
            self._pid = _OutputDebugStringLogger._pid_to_winpid(pid)
            logging.debug("Attached to process %d (winpid %d)", pid, self._pid)

        def run(self):
            pid_length = 4
            data_length = self._bufsize - pid_length

            # Signal that the buffer is available
            _KERNEL32.SetEvent(self._buffer_ev)

            events = [self._data_ev, self._stop_ev]
            while True:
                result = _KERNEL32.WaitForMultipleObjects(
                    len(events), (ctypes.c_void_p * len(events))(*events), 0, INFINITE
                )
                if result == WAIT_OBJECT_0:
                    pid_data = ctypes.string_at(self._buffer, pid_length)
                    (pid,) = struct.unpack('I', pid_data)
                    data = ctypes.string_at(self._buffer + pid_length, data_length)

                    # Signal that the buffer is available
                    _KERNEL32.SetEvent(self._buffer_ev)

                    if pid != self._pid:
                        continue

                    self._pipe_in.write(data[: data.index(0)])
                    self._pipe_in.flush()

                elif result == WAIT_OBJECT_1:
                    break

                else:
                    time.sleep(0.100)

        def stop(self):
            '''Stops this OutputDebugStringLogger'''
            _KERNEL32.SetEvent(self._stop_ev)
            self.join()
            _KERNEL32.UnmapViewOfFile(self._buffer)
            _KERNEL32.CloseHandle(self._mapping)
            self._pipe_in.close()

            self.output.close()


if nimp.sys.platform.is_windows():

    class Monitor(threading.Thread):
        '''Watchdog killing child processes when nimp ends'''

        def __init__(self):
            super().__init__()
            self._watcher_event_handle = _KERNEL32.CreateEventW(None, 0, 0, None)
            if self._watcher_event_handle == 0:
                logging.error("cannot create event")
            self._nimp_handle = _KERNEL32.OpenProcess(
                PROCESS_SYNCHRONIZE | PROCESS_QUERY_INFORMATION, False, os.getppid()
            )
            if self._nimp_handle == 0:
                logging.error("cannot open nimp process")

        def run(self):
            events = [self._nimp_handle, self._watcher_event_handle]
            while True:
                result = _KERNEL32.WaitForMultipleObjects(
                    len(events), (ctypes.c_void_p * len(events))(*events), 0, INFINITE
                )
                if result == WAIT_OBJECT_0:
                    logging.debug(
                        "Parent nimp.exe is not running anymore: current python process and its subprocesses are going to be killed"
                    )
                    call(['taskkill', '/F', '/T', '/PID', str(os.getpid())])
                    break
                elif result == WAIT_OBJECT_1:
                    break

        def stop(self):
            '''Stops this monitor'''
            _KERNEL32.CloseHandle(self._nimp_handle)
            _KERNEL32.SetEvent(self._watcher_event_handle)

else:

    class Monitor:
        def start(self):
            pass

        def stop(self):
            pass
