# -*- coding: utf-8 -*-

import os
import ctypes

import sys
import threading
import subprocess
import struct
import time

from nimp.utilities.logging import *

class my_void_p(ctypes.c_void_p):
    # Subclassing c_void_p prevents implicit casts to int
    pass

windll = None

class WinDLL():
    def __init__(self):
        self._kernel32 = ctypes.cdll.LoadLibrary("kernel32.dll")

        # ensure we got the right DLL
        self._kernel32.GetLastError()

        # import only the functions we need
        self.CreateEvent = self._kernel32.CreateEventW
        self.CreateEvent.restype = my_void_p
        self.CreateEvent.argtypes = [my_void_p,
                                     ctypes.c_int,
                                     ctypes.c_int,
                                     ctypes.c_wchar_p]

        self.CreateFileMapping = self._kernel32.CreateFileMappingW
        self.CreateFileMapping.restype = my_void_p
        self.CreateFileMapping.argtypes = [my_void_p,
                                           my_void_p,
                                           ctypes.c_int,
                                           ctypes.c_int,
                                           ctypes.c_int,
                                           ctypes.c_wchar_p]

        self.SetEvent = self._kernel32.SetEvent
        self.SetEvent.restype = ctypes.c_int
        self.SetEvent.argtypes = [my_void_p]

        self.WaitForMultipleObjects = self._kernel32.WaitForMultipleObjects
        self.WaitForMultipleObjects.restype = ctypes.c_int
        self.WaitForMultipleObjects.argtypes = [ctypes.c_int,
                                                my_void_p,
                                                ctypes.c_int,
                                                ctypes.c_int]

        self.MapViewOfFile = self._kernel32.MapViewOfFile
        self.MapViewOfFile.restype = my_void_p
        self.MapViewOfFile.argtypes = [my_void_p,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int,
                                       ctypes.c_int]

        self.UnmapViewOfFile = self._kernel32.UnmapViewOfFile
        self.UnmapViewOfFile.restype = ctypes.c_int
        self.UnmapViewOfFile.argtypes = [my_void_p]

        self.CloseHandle = self._kernel32.CloseHandle
        self.CloseHandle.restype = ctypes.c_int
        self.CloseHandle.argtypes = [my_void_p]

        self.SetErrorMode = self._kernel32.SetErrorMode
        self.SetErrorMode.restype = ctypes.c_int
        self.SetErrorMode.argtypes = [ctypes.c_int]

        # Constants from winbase.h and others
        self.INVALID_HANDLE_VALUE = my_void_p(-1).value

        self.WAIT_OBJECT_0 = 0x00000000
        self.WAIT_OBJECT_1 = 0x00000001
        self.INFINITE      = 0xFFFFFFFF

        self.PAGE_READWRITE = 0x4

        self.FILE_MAP_READ = 0x0004

        self.SEM_FAILCRITICALERRORS = 0x0001
        self.SEM_NOGPFAULTERRORBOX  = 0x0002
        self.SEM_NOOPENFILEERRORBOX = 0x8000


#
# Disable “Entry Point Not Found” and “Application Error” dialogs for child processes
#
def disable_win32_dialogs():
    try:
        global windll
        windll = windll or WinDLL()
    except:
        return

    windll.SetErrorMode(windll.SEM_FAILCRITICALERRORS \
                         | windll.SEM_NOGPFAULTERRORBOX \
                         | windll.SEM_NOOPENFILEERRORBOX)


#-------------------------------------------------------------------------------
class OutputDebugStringLogger(threading.Thread):
    def __init__(self):
        super().__init__()

        try:
            global windll
            windll = windll or WinDLL()
        except:
            self.output = open(os.devnull, 'rb')
            return

        fd_in, fd_out = os.pipe()
        self.output = os.fdopen(fd_in, 'rb')
        self._pipe_in = os.fdopen(fd_out, 'wb')

        self._buffer_ev = windll.CreateEvent(None, 0, 0, 'DBWIN_BUFFER_READY')
        self._data_ev = windll.CreateEvent(None, 0, 0, 'DBWIN_DATA_READY')
        self._stop_ev = windll.CreateEvent(None, 0, 0, None)
        self._bufsize = 4096

        self._mapping = windll.CreateFileMapping(windll.INVALID_HANDLE_VALUE,
                                                 None,
                                                 windll.PAGE_READWRITE,
                                                 0,
                                                 self._bufsize,
                                                 'DBWIN_BUFFER');
        self._buffer = windll.MapViewOfFile(self._mapping,
                                            windll.FILE_MAP_READ,
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
        if not windll:
            return

        self._pid = self._pid_to_winpid(pid)
        log_verbose("Attached to process %d (winpid %d)" % (pid, self._pid))

    def run(self):
        if not windll:
            return

        pid_length = 4
        data_length = self._bufsize - pid_length

        # Signal that the buffer is available
        windll.SetEvent(self._buffer_ev)

        events = [self._data_ev, self._stop_ev]
        while True:
            result = windll.WaitForMultipleObjects(len(events),
                                                   (my_void_p * len(events))(*events),
                                                   0,
                                                   windll.INFINITE)
            if result == windll.WAIT_OBJECT_0:
                pid, = struct.unpack('I', ctypes.string_at(self._buffer.value, pid_length))
                data = ctypes.string_at(self._buffer.value + pid_length, data_length)

                # Signal that the buffer is available
                windll.SetEvent(self._buffer_ev)

                if pid != self._pid:
                    continue

                self._pipe_in.write(data[:data.index(0)])
                self._pipe_in.flush()

            elif result == windll.WAIT_OBJECT_1:
                break

            else:
                time.sleep(0.100)

    def stop(self):
        if not windll:
            self.join()
        else:
            windll.SetEvent(self._stop_ev)
            self.join()
            windll.UnmapViewOfFile(self._buffer)
            windll.CloseHandle(self._mapping)
            self._pipe_in.close()

        self.output.close()

