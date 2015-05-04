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

from nimp.utilities.environment      import *
from nimp.utilities.build        import *
from nimp.utilities.deployment   import *

def generate_gp4(env, dest_dir):
    packages_config = env.packages_config

    if hasattr(packages_config, "__call__"):
        packages_config = packages_config(env)
    else:
        packages_config = packages_config[env.dlc]

    for package in packages_config:
        mandatory_keys_error_format = "{{key}} should be defined in gp4 settings for {dlc}".format(dlc = env.dlc)
        if not check_keys(package, mandatory_keys_error_format, 'gp4_file', 'volume_type', 'content_id', 'passcode'):
            return False

        gp4_file = env.format(os.path.join(dest_dir, package['gp4_file']), **package)

        if os.path.exists(gp4_file):
            os.remove(gp4_file)
        create_gp4_command = ['orbis-pub-cmd.exe',
                              'gp4_proj_create',
                              '--volume_type', package['volume_type'],
                              '--content_id',  package['content_id'],
                              '--passcode',    package['passcode'] ]

        volume_type = package['volume_type']
        if volume_type == 'pkg_ps4_app' or volume_type == 'pkg_ps4_patch':
            if not check_keys(package, mandatory_keys_error_format, 'storage_type'):
                return False
            if 'app_type' in package:
                create_gp4_command += ["--app_type", package['app_type'] ]

            create_gp4_command += ["--storage_type", package['storage_type'],
                                   "--passcode", package['passcode'] ]

        if volume_type == 'pkg_ps4_patch':
            if not check_keys(package, mandatory_keys_error_format, 'app_path'):
                return False
            create_gp4_command += ["--app_path", package['app_path'] ]

            if 'latest_patch_path' in package:
                create_gp4_command += ["--latest_patch_path", package['latest_patch_path'] ]
            if 'patch_type' in package:
                create_gp4_command += ["--patch_type", package['patch_type'] ]

        if volume_type == 'pkg_ps4_ac_data' or volume_type == 'pkg_ps4_ac_nodata':
            if not check_keys(package, mandatory_keys_error_format, 'entitlement_key'):
                return False
                create_gp4_command += ["--entitlement_key", package['entitlement_key'] ]

        create_gp4_command += [gp4_file]

        if call_process('.', create_gp4_command) != 0:
            return False

        if 'chunks' in package:
            for chunk in package['chunks']:
                mandatory_keys_error_format = "{key} should be defined in chunk."
                if not check_keys(chunk, mandatory_keys_error_format, 'id'):
                    return False
                add_chunk_command = ["orbis-pub-cmd.exe", "gp4_chunk_add", "--id", chunk['id'] ]

                if 'label' in chunk:
                    add_chunk_command += ["--label", chunk['label']]

                if 'languages' in chunk:
                    add_chunk_command += ["--languages", chunk['languages']]

                if 'layer_no' in chunk:
                    add_chunk_command += ["--layer_no", chunk['layer_no']]

                add_chunk_command += [gp4_file]
                if call_process('.', add_chunk_command) != 0:
                    return False

        pkg_files = env.map_files().override(**package).src(dest_dir)
        pkg_files.load_set(env.packages_config_file)

        for source, destination in pkg_files():
            log_notification("{0}   {1}", source, destination)
            destination = destination.replace('\\', '/')
            if call_process('.', ['orbis-pub-cmd.exe',  'gp4_file_add', source, destination, gp4_file]) != 0:
                return False

    return True

#-------------------------------------------------------------------------------
def ps4_generate_pkgs(env, loose_files_dir, dest_dir):
    packages_config = env.packages_config

    if hasattr(packages_config, "__call__"):
        packages_config = packages_config(env)
    else:
        packages_config = packages_config[env.dlc]

    for package in packages_config:
        mandatory_keys_error_format = "{{key}} should be defined in gp4 settings for {dlc}".format(dlc = env.dlc)
        if not check_keys(package, mandatory_keys_error_format, 'gp4_file', 'pkg_dest'):
            return False

        gp4_file = env.format(os.path.join(loose_files_dir, package['gp4_file']), **package)
        pkg_file = env.format(os.path.join(dest_dir, package['pkg_dest']), **package)
        dest_dir = os.path.dirname(pkg_file)
        safe_makedirs(dest_dir)

        if call_process(dest_dir, ["orbis-pub-cmd.exe", "img_create", gp4_file, pkg_file]) != 0:
            return False

    return True
