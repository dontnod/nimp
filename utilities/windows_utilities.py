# -*- coding: utf-8 -*-

import winreg;
import os
import sys
import win32event
import threading
import struct
import mmap

#-------------------------------------------------------------------------------
def get_key_value(root, key_path, sub_key_name):
    splitted_key_path   = key_path.split("\\")
    current_key         = root
    result              = None
    try:
        for next_key_path in splitted_key_path:
            current_key = winreg.OpenKey(current_key, next_key_path)
        (result, type) = winreg.QueryValueEx(current_key, sub_key_name)
    except WindowsError as error:
        log_error("Error while reading registry key {0}{1} : {2}", key_path, sub_key_name, error)
        pass

    return result.decode('utf-8')

class OutputDebugStringLogger(threading.Thread):
    def __init__(self):
        super().__init__()

        self._filtered_pids             = []
        fd_in, fd_out                   = os.pipe()
        self.output                     = os.fdopen(fd_in, 'rb')
        self._pipe_in                   = os.fdopen(fd_out, 'wb')
        self._buffer_ready_event        = win32event.CreateEvent(None, 0, 0, "DBWIN_BUFFER_READY")
        self._data_ready_event          = win32event.CreateEvent(None, 0, 0, "DBWIN_DATA_READY")
        self._stop_event                = win32event.CreateEvent(None, 0, 0, None)
        self._buffer_length             = 4096
        self._buffer                    = mmap.mmap (0, self._buffer_length, "DBWIN_BUFFER", mmap.ACCESS_WRITE)

    def log_process_output(self, pid):
        self._filtered_pids.append(pid)

    def run(self):
        process_id_length   = 4
        remaining_length    = self._buffer_length - process_id_length
        events              = [self._data_ready_event, self._stop_event]
        while True:
            win32event.SetEvent(self._buffer_ready_event)
            result = win32event.WaitForMultipleObjects(events, 0, win32event.INFINITE)
            if result == win32event.WAIT_OBJECT_0:
                self._buffer.seek(0)
                process_id, = struct.unpack('L', self._buffer.read(process_id_length))

                if process_id not in self._filtered_pids:
                    continue

                data        = self._buffer.read(remaining_length)
                self._pipe_in.write(data[:data.index(0)])
            elif result == (win32event.WAIT_OBJECT_0 + 1):
                break

    def stop(self):
        win32event.SetEvent(self._stop_event)
        self.join()
        self._pipe_in.close()
        self.output.close()