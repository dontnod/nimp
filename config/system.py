# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
import os

#-------------------------------------------------------------------------------
# Constants
#-------------------------------------------------------------------------------
LINUX    = 0
WINDOWS  = 1

if os.name == "posix":
    OS                                  = LINUX
    PLATFORM_NAME                       = "linux"
    USER_DIRECTORY_ENVIRONMENT_VARIABLE = "HOME"
else:
    OS                                  = WINDOWS
    PLATFORM_NAME                       = "windows"
    USER_DIRECTORY_ENVIRONMENT_VARIABLE = "APPDATA"

#-------------------------------------------------------------------------------
# os_dependent
def os_dependent(linux, windows):
    if OS == LINUX:
        return linux
    elif OS == WINDOWS:
        return windows
    else:
        assert(False)

#-------------------------------------------------------------------------------
# os_dependent_exe
def executable_name(name_without_extension):
    return os_dependent(linux   = name_without_extension,
                        windows = name_without_extension + ".exe")