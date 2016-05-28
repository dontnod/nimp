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
''' Windows specific stuff '''

import ctypes
import logging
import os
import struct
import threading
import time

import nimp.system

_KERNEL32 = ctypes.windll.kernel32 if hasattr(ctypes, 'windll') else None

INVALID_HANDLE_VALUE = -1 # Should be c_void_p(-1).value but doesn’t work

WAIT_OBJECT_0 = 0x00000000
WAIT_OBJECT_1 = 0x00000001
INFINITE      = 0xFFFFFFFF

PAGE_READWRITE = 0x4

FILE_MAP_READ = 0x0004

SEM_FAILCRITICALERRORS = 0x0001
SEM_NOGPFAULTERRORBOX  = 0x0002
SEM_NOOPENFILEERRORBOX = 0x8000

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SYNCHRONIZE = 0x00100000

def disable_win32_dialogs():
    ''' Disable “Entry Point Not Found” and “Application Error” dialogs for
        child processes '''

    _KERNEL32.SetErrorMode(SEM_FAILCRITICALERRORS \
                        | SEM_NOGPFAULTERRORBOX \
                        | SEM_NOOPENFILEERRORBOX)

class NimpMonitor(threading.Thread):
    ''' Watchdog killing child processes when nimp ends '''
    def __init__(self):
        super().__init__()
        self._watcher_event_handle = _KERNEL32.CreateEventW(None, 0, 0, None)
        if self._watcher_event_handle == 0:
            logging.error("cannot create event")
        self._nimp_handle = _KERNEL32.OpenProcess(PROCESS_SYNCHRONIZE | PROCESS_QUERY_INFORMATION, False, os.getppid())
        if self._nimp_handle == 0:
            logging.error("cannot open nimp process")

    def run(self):
        events = [self._nimp_handle, self._watcher_event_handle]
        while True:
            result = _KERNEL32.WaitForMultipleObjects(len(events), (ctypes.c_void_p * len(events))(*events), 0, INFINITE)
            if result == WAIT_OBJECT_0:
                logging.debug("Parent nimp.exe is not running anymore: current python process and its subprocesses are going to be killed")
                nimp.system.call_process('.', ['taskkill', '/F', '/T', '/PID', str(os.getpid())])
                break
            elif result == WAIT_OBJECT_1:
                break

    def stop(self):
        ''' Stops this monitor '''
        _KERNEL32.CloseHandle(self._nimp_handle)
        _KERNEL32.SetEvent(self._watcher_event_handle)

class OutputDebugStringLogger(threading.Thread):
    ''' Get output debug string from a process and writes it to a pipe '''
    def __init__(self):
        super().__init__()

        fd_in, fd_out = os.pipe()
        self.output = os.fdopen(fd_in, 'rb')
        self._pipe_in = os.fdopen(fd_out, 'wb')

        self._buffer_ev = _KERNEL32.CreateEventW(None, 0, 0, 'DBWIN_BUFFER_READY')
        self._data_ev = _KERNEL32.CreateEventW(None, 0, 0, 'DBWIN_DATA_READY')
        self._stop_ev = _KERNEL32.CreateEventW(None, 0, 0, None)
        self._bufsize = 4096

        self._mapping = _KERNEL32.CreateFileMappingW(INVALID_HANDLE_VALUE,
                                                     None,
                                                     PAGE_READWRITE,
                                                     0,
                                                     self._bufsize,
                                                     'DBWIN_BUFFER')
        self._buffer = _KERNEL32.MapViewOfFile(self._mapping,
                                               FILE_MAP_READ,
                                               0, 0,
                                               self._bufsize)
        self._pid = None

    @staticmethod
    def _pid_to_winpid(pid):
        # In case we’re running in MSYS2 Python, the PID we got is actually an
        # internal MSYS2 PID, and the PID we want to watch is actually the WINPID,
        # which we retrieve in /proc
        try:
            return int(open("/proc/%d/winpid" % (pid,)).read(10))
        #pylint: disable=broad-except
        except Exception:
            return pid

    def attach(self, pid):
        ''' Sets the process pid from wich to capture output debug string '''
        self._pid = OutputDebugStringLogger._pid_to_winpid(pid)
        logging.debug("Attached to process %d (winpid %d)", pid, self._pid)

    def run(self):
        pid_length = 4
        data_length = self._bufsize - pid_length

        # Signal that the buffer is available
        _KERNEL32.SetEvent(self._buffer_ev)

        events = [self._data_ev, self._stop_ev]
        while True:
            result = _KERNEL32.WaitForMultipleObjects(len(events),
                                                      (ctypes.c_void_p * len(events))(*events),
                                                      0,
                                                      INFINITE)
            if result == WAIT_OBJECT_0:
                pid, = struct.unpack('I', ctypes.string_at(self._buffer, pid_length))
                data = ctypes.string_at(self._buffer + pid_length, data_length)

                # Signal that the buffer is available
                _KERNEL32.SetEvent(self._buffer_ev)

                if pid != self._pid:
                    continue

                self._pipe_in.write(data[:data.index(0)])
                self._pipe_in.flush()

            elif result == WAIT_OBJECT_1:
                break

            else:
                time.sleep(0.100)

    def stop(self):
        ''' Stops this OutputDebugStringLogger '''
        _KERNEL32.SetEvent(self._stop_ev)
        self.join()
        _KERNEL32.UnmapViewOfFile(self._buffer)
        _KERNEL32.CloseHandle(self._mapping)
        self._pipe_in.close()

        self.output.close()

