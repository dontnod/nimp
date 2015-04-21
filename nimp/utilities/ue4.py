# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
import shutil
import os

from nimp.utilities.build            import *
from nimp.utilities.deployment       import *

#---------------------------------------------------------------------------
def ue4_build(context):
    return True

#---------------------------------------------------------------------------
def ue4_ship(context, destination = None):
    return True

#---------------------------------------------------------------------------
def ue4_cook(context, destination = None):
    return True