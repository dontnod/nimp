#!/usr/bin/env python

import os
import shutil
import sys

# Update version below and:
#  python3 setup.py bdist
#  python3 setup.py sdist upload
VERSION = '0.0.11'

setup_info = dict(

    name = 'nimp-cli',
    version = VERSION,
    description = 'Multipurpose build tool',
    long_description = '' +
        'Nimp is a cross-platform tool that helps maintain, compile, cook, ' +
        'and ship game projects. It currently supports Unreal Engine.' +
        '',
    license = 'MIT',

    url = 'https://github.com/dontnod/nimp',
    download_url = 'https://github.com/dontnod/nimp/tarball/' + VERSION,

    author = 'Dontnod Entertainment',
    author_email = 'root@dont-nod.com',

    packages = [
        'nimp',
        'nimp/commands',
        'nimp',
    ],

    install_requires = [
        'glob2',
        'python-magic',
    ],

    entry_points = {
        'console_scripts' : [ 'nimp = nimp.nimp_cli:main' ],
    },

    # See list at https://pypi.python.org/pypi?:action=list_classifiers
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development :: Build Tools',
    ],

    keywords = 'build compile unrealengine',
)

setuptools_info = dict(
    zip_safe = True,
)

from setuptools import setup
setup(**setup_info)

