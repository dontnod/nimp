#!/usr/bin/env python

import subprocess

import setuptools


def _try_get_revision():
    try:
        output = subprocess.check_output([ 'git', 'rev-parse', '--short=10', 'HEAD' ])
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return output.decode('utf-8').strip()


# Update version below and:
#  python3 setup.py bdist
#  python3 setup.py sdist upload
version_short = '0.3.2'

revision = _try_get_revision()
version_full = version_short + ('+' + revision if revision else '')

setup_info = dict(

    name = 'nimp-cli',
    version = version_full,
    description = 'Multipurpose build tool',
    long_description = '' +
        'Nimp is a cross-platform tool that helps maintain, compile, cook, ' +
        'and ship game projects. It currently supports Unreal Engine.' +
        '',
    license = 'MIT',

    url = 'https://github.com/dontnod/nimp',
    download_url = 'https://github.com/dontnod/nimp/archive/' + version_short + '.tar.gz',

    author = 'Dontnod Entertainment',
    author_email = 'root@dont-nod.com',

    packages = [
        'nimp',
        'nimp/commands',
        'nimp/sys',
        'nimp/utils',
    ],

    install_requires = [
        'glob2',
        'python-magic',
        'requests',
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

setuptools.setup(**setup_info)
