# -*- coding: utf-8 -*-

import os
import ctypes

import sys
import threading
import subprocess
import struct
import time

from nimp.utilities.logging import *

kernel32 = ctypes.windll.kernel32

INVALID_HANDLE_VALUE = -1 # Should be c_void_p(-1).value but doesn’t work

WAIT_OBJECT_0 = 0x00000000
WAIT_OBJECT_1 = 0x00000001
INFINITE      = 0xFFFFFFFF

PAGE_READWRITE = 0x4

FILE_MAP_READ = 0x0004

SEM_FAILCRITICALERRORS = 0x0001
SEM_NOGPFAULTERRORBOX  = 0x0002
SEM_NOOPENFILEERRORBOX = 0x8000


#
# Disable “Entry Point Not Found” and “Application Error” dialogs for child processes
#
def disable_win32_dialogs():
    kernel32.SetErrorMode(SEM_FAILCRITICALERRORS \
                        | SEM_NOGPFAULTERRORBOX \
                        | SEM_NOOPENFILEERRORBOX)


#-------------------------------------------------------------------------------
class OutputDebugStringLogger(threading.Thread):
    def __init__(self):
        super().__init__()

        fd_in, fd_out = os.pipe()
        self.output = os.fdopen(fd_in, 'rb')
        self._pipe_in = os.fdopen(fd_out, 'wb')

        self._buffer_ev = kernel32.CreateEventW(None, 0, 0, 'DBWIN_BUFFER_READY')
        self._data_ev = kernel32.CreateEventW(None, 0, 0, 'DBWIN_DATA_READY')
        self._stop_ev = kernel32.CreateEventW(None, 0, 0, None)
        self._bufsize = 4096

        self._mapping = kernel32.CreateFileMappingW(INVALID_HANDLE_VALUE,
                                                    None,
                                                    PAGE_READWRITE,
                                                    0,
                                                    self._bufsize,
                                                    'DBWIN_BUFFER');
        self._buffer = kernel32.MapViewOfFile(self._mapping,
                                              FILE_MAP_READ,
                                              0, 0,
                                              self._bufsize)

    def _pid_to_winpid(self, pid):
        # In case we’re running in MSYS2 Python, the PID we got is actually an
        # internal MSYS2 PID, and the PID we want to watch is actually the WINPID,
        # which we retrieve in /proc
        try:
            return int(open("/proc/%d/winpid" % (pid,)).read(10))
        except:
            return pid

    def attach(self, pid):
        self._pid = self._pid_to_winpid(pid)
        log_verbose("Attached to process %d (winpid %d)" % (pid, self._pid))

    def run(self):
        pid_length = 4
        data_length = self._bufsize - pid_length

        # Signal that the buffer is available
        kernel32.SetEvent(self._buffer_ev)

        events = [self._data_ev, self._stop_ev]
        while True:
            result = kernel32.WaitForMultipleObjects(len(events),
                                                     (ctypes.c_void_p * len(events))(*events),
                                                     0,
                                                     INFINITE)
            if result == WAIT_OBJECT_0:
                pid, = struct.unpack('I', ctypes.string_at(self._buffer, pid_length))
                data = ctypes.string_at(self._buffer + pid_length, data_length)

                # Signal that the buffer is available
                kernel32.SetEvent(self._buffer_ev)

                if pid != self._pid:
                    continue

                self._pipe_in.write(data[:data.index(0)])
                self._pipe_in.flush()

            elif result == WAIT_OBJECT_1:
                break

            else:
                time.sleep(0.100)

    def stop(self):
        kernel32.SetEvent(self._stop_ev)
        self.join()
        kernel32.UnmapViewOfFile(self._buffer)
        kernel32.CloseHandle(self._mapping)
        self._pipe_in.close()

        self.output.close()

