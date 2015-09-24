# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
import shutil
import os
import os.path

from nimp.utilities.environment import *
from nimp.utilities.build import *
from nimp.utilities.deployment import *

def generate_chunk_xml(env, dest_dir):
    packages_config = env.packages_config

    if hasattr(packages_config, "__call__"):
        packages_config = packages_config(env)
    else:
        packages_config = packages_config[env.dlc]

    for package in packages_config:
        src_file = env.format(package['manifest'], **package)
        dst_file = env.format(os.path.join(dest_dir, package['temp_dir'], 'appxmanifest.xml'), **package)
        robocopy(src_file, dst_file)

        src_file = env.format(package['chunk_file'], **package)
        dst_file = env.format(os.path.join(dest_dir, package['temp_dir'], 'chunk.xml'), **package)
        robocopy(src_file, dst_file)

        pkg_files = env.map_files().override(**package).src(dest_dir)
        pkg_files.load_set(env.packages_config_file)

        for src, dst in pkg_files():
            dst = dst.replace('\\', '/')

    return True

#-------------------------------------------------------------------------------
def xboxone_generate_pkgs(env, loose_files_dir, destination):
    packages_config = env.packages_config

    if hasattr(packages_config, "__call__"):
        packages_config = packages_config(env)
    else:
        packages_config = packages_config[env.dlc]

    for package in packages_config:
        mandatory_keys_error_format = "{{key}} should be defined in package settings for {dlc}".format(dlc = env.dlc)
        if not check_keys(package, mandatory_keys_error_format, 'temp_dir', 'manifest'):
            return False

        src_dir = env.format(os.path.join(loose_files_dir, package['temp_dir']), **package)
        dest_dir = env.format(destination, **package)

        safe_makedirs(src_dir)
        safe_makedirs(dest_dir)

        # Build appdata.bin
        command = [ os.getenv('DurangoXDK') + 'bin/makepkg.exe',
                    'appdata',
                    '/f', env.format(package['manifest']),
                    '/pd', src_dir ]

        if call_process('.', command) != 0:
            return False

        command = [ os.getenv('DurangoXDK') + 'bin/makepkg.exe',
                    'pack',
                    '/v',
                    '/lt',
                    '/f', env.format(package['chunk_file']),
                    '/d', src_dir,
                    '/pd', env.format('{game}/Tmp'),
                    '/productid', package['product_id'],
                    '/contentid', package['content_id'],
                    '/updcompat', '2' ]

        if call_process('.', command, heartbeat = 30) != 0:
            return False

        # Verify package but do not fail job if the verification fails
        #call_process(dest_dir, [ "orbis-pub-cmd", "img_verify", "--passcode", package['passcode'], pkg_file ])

    return True

