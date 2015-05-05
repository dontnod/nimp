# -*- coding: utf-8 -*-

ODS_ENABLED = True

import os
import sys
import threading
import struct
import mmap

try:
    import win32event
    import winreg;
except:
    ODS_ENABLED = False

#-------------------------------------------------------------------------------
class OutputDebugStringLogger(threading.Thread):
    def __init__(self):
        super().__init__()
        fd_in, fd_out            = os.pipe()
        self.output              = os.fdopen(fd_in, 'rb')
        self._pipe_in            = os.fdopen(fd_out, 'wb')
        self._buffer_ready_event = win32event.CreateEvent(None, 0, 0, "DBWIN_BUFFER_READY")
        self._data_ready_event   = win32event.CreateEvent(None, 0, 0, "DBWIN_DATA_READY")
        self._stop_event         = win32event.CreateEvent(None, 0, 0, None)
        self._buffer_length      = 4096
        self._buffer             = mmap.mmap (0, self._buffer_length, "DBWIN_BUFFER", mmap.ACCESS_WRITE)

    def attach(self, pid):
        self._pid = pid

    def run(self):
        process_id_length = 4
        remaining_length = self._buffer_length - process_id_length
        events = [self._data_ready_event, self._stop_event]
        while True:
            win32event.SetEvent(self._buffer_ready_event)
            result = win32event.WaitForMultipleObjects(events, 0, win32event.INFINITE)
            if result == win32event.WAIT_OBJECT_0:
                self._buffer.seek(0)
                process_id, = struct.unpack('L', self._buffer.read(process_id_length))

                if process_id != self._pid:
                    continue

                data = self._buffer.read(remaining_length)
                self._pipe_in.write(data[:data.index(0)])
            elif result == (win32event.WAIT_OBJECT_0 + 1):
                break

    def stop(self):
        win32event.SetEvent(self._stop_event)
        self.join()
        self._pipe_in.close()
        self.output.close()
