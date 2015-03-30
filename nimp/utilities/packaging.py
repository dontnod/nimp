# -*- coding: utf-8 -*-

from datetime import date

import os
import io
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

from nimp.utilities.processes  import *
from nimp.utilities.ps3        import *

#---------------------------------------------------------------------------
def generate_pkg_config(context):
    # Set various file path
    toc_files = ['C:\\DNE\\PG3\\UnrealEngine3\\ExampleGame\\PS4FINALTOC_Episode03.txt',
                  'C:\\DNE\\PG3\\UnrealEngine3\\ExampleGame\\PS4FINALTOC_FRA_Episode03.txt']

    gp4_template_file = 'C:\\DNE\\PG3\\UnrealEngine3\\ExampleGame\\Build\\Buildbot\\PS4\Dlc\\GP4_TEMPLATES\\templateSCEA.gp4'
    gp4_file = 'C:\\DNE\\PG3\\UnrealEngine3\\ExampleGame\\Build\\Buildbot\\PS4\Dlc\\GP4_TEMPLATES\\Episode03-SCEA.gp4'

    # Retrieve data from toc_files in toc_content[]
    toc_content=[]
    for toc_file in toc_files:
        with open(toc_file) as input:
            toc_content += input.readlines()

    #Remove unwanted stuff trom toc_content[]
    new_toc_content=[]
    for line in toc_content:
        line =  line.split(' 0 ', 1)[-1].split(' 0', 1)[0]
        new_toc_content.append(line)
    toc_content = new_toc_content

    #Create gp4_file from gp4_template_file
    preFile = io.open(gp4_template_file, 'r')
    with open(gp4_file, 'w') as input:
        input.writelines(preFile.readlines())
    preFile.close()


    # Add proper content_id to gp4_file
    call_process('.', ['orbis-pub-cmd.exe', 'gp4_proj_update', '--toc_content_id', 'UP0082-CUSA01442_00', gp4_file])

    pkg_files = context.map_files().override(territory = 'SCEA')
    pkg_files.load_set("Package")

    # Add toc_content[] to gp4_file
    for source, destination in pkg_files():
        log_notification("{0}   {1}", source, destination)
        destination = destination.replace('\\', '/')
        call_process('.', ['orbis-pub-cmd.exe',  'gp4_file_add', source, destination, gp4_file])

    # That's it! for now...
    return True

#---------------------------------------------------------------------------
def make_packages(context, source, destination):
    if context.is_ps3:
        return ps3_generate_pkgs(context, source, destination)
    return True
