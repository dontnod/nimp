# -*- coding: utf-8 -*-

from datetime import date

import os
import stat
import os.path
import tempfile;
import shutil
import stat
import glob
import fnmatch
import re
import contextlib
import pathlib

from nimp.utilities.ps3      import *

#---------------------------------------------------------------------------
def make_packages(context, source, destination):
    if context.is_ps3:
        return ps3_generate_pkgs(context, source, destination)
    return True
