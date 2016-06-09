#!/usr/bin/env python

import os
import shutil
import sys

VERSION = '0.0.0git'

setup_info = dict(

    name = 'nimp',
    version = VERSION,
    author = 'Dontnod Entertainment',
    description = 'DNE build tool',

    packages = [
        'nimp',
        'nimp/commands',
        'nimp',
    ],

    install_requires = [
        'glob2'
    ],

    entry_points = {
        'console_scripts' : [ 'nimp = nimp.nimp_cli:main' ],
    },
)

setuptools_info = dict(
    zip_safe = True,
)

from setuptools import setup
setup(**setup_info)

