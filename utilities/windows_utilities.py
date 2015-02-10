# -*- coding: utf-8 -*-

import winreg;
import os
import sys

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
