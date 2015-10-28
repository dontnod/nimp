# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
import shutil
import fnmatch
import os
import os.path

from nimp.utilities.environment import *
from nimp.utilities.build import *
from nimp.utilities.deployment import *

def generate_gp4(env, dest_dir):
    packages_config = env.packages_config

    if hasattr(packages_config, "__call__"):
        packages_config = packages_config(env)
    else:
        packages_config = packages_config[env.dlc]

    for package in packages_config:
        mandatory_keys_error_format = "{{key}} should be defined in gp4 settings for {dlc}".format(dlc = env.dlc)
        if not check_keys(package, mandatory_keys_error_format,
                          'gp4_file',
                          'volume_id',
                          'volume_type',
                          'content_id',
                          'passcode'):
            return False

        gp4_file = env.format(os.path.join(dest_dir, package['gp4_file']), **package)

        if os.path.exists(gp4_file):
            os.remove(gp4_file)
        create_gp4_command = ['orbis-pub-cmd.exe',
                              'gp4_proj_create',
                              #'--volume_id',   package['volume_id'],
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
            if 'entitlement_key' in package:
                create_gp4_command += ["--entitlement_key", package['entitlement_key'] ]

        create_gp4_command += [gp4_file]

        if call_process('.', create_gp4_command) != 0:
            return False

        if 'chunks' in package:

            for chunk in package['chunks']:
                mandatory_keys_error_format = "{key} should be defined in chunk."
                if not check_keys(chunk, mandatory_keys_error_format, 'id'):
                    return False

            # Iterate over chunks by increasing ID
            for ignored, chunk in sorted([(int(chunk['id']), chunk) for chunk in package['chunks']]):

                add_chunk_command = [ 'orbis-pub-cmd.exe',
                                      'gp4_chunk_update' if chunk['id'] == '0' else 'gp4_chunk_add',
                                      '--id', chunk['id'] ]

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

        # Remember all directories to which we stored files
        known_paths = {}
        gp4_contents = None

        for src, dst in pkg_files():
            dst = dst.replace('\\', '/')

            chunk_id = ''
            if 'chunks' in package:
                for chunk in package['chunks']:
                    if 'files' not in chunk or True in [fnmatch.fnmatch(dst, g) for g in chunk['files']]:
                        chunk_id = chunk['id']
                        break

            # Speed optimisation: if we have already stored a file in this directory,
            # directly edit the GP4 file and copy the relevant line. This is orders of
            # magnitude faster than running orbis-pub-cmd.exe.
            # The file being added must have same source and destination filename.
            # The GP4 line we copy must have same source and target dir _and_ same
            # extension (because we handle compression differently).

            key = '%s|%s|%s|%s' % (os.path.dirname(src), os.path.dirname(dst), os.path.splitext(dst)[1].lower(), chunk_id)

            file_is_renamed = os.path.basename(src) != os.path.basename(dst)
            shortcut = False

            if not file_is_renamed and key in known_paths:
                if gp4_contents is None:
                    gp4_contents = open(gp4_file).readlines()
                pattern = known_paths[key]

                for n in range(len(gp4_contents)):
                    line = gp4_contents[n]
                    # Check for the whole path…
                    if pattern not in line.replace('\\', '/'):
                        continue
                    # … but only replace the filename
                    line = line.replace(os.path.basename(pattern), os.path.basename(dst))
                    if line != gp4_contents[n]:
                        log_notification("Directly adding {0} → {1} to {2}", src, dst, gp4_file)
                        gp4_contents = gp4_contents[:n + 1] + [ line ] + gp4_contents[n + 1:]
                        shortcut = True
                        break

            if not shortcut:
                # Save in-memory GP4 contents first
                if gp4_contents is not None:
                    with open(gp4_file, 'w') as f:
                        f.writelines(gp4_contents)
                        gp4_contents = None

                # Now call orbis-pub-cmd
                add_file_command = [ 'orbis-pub-cmd.exe', 'gp4_file_add' ]

                if os.path.splitext(dst)[1].lower() in [ '.bin', '.bnk', '.pck', '.xxx' ]:
                    add_file_command += [ '--pfs_compression', 'enable' ]

                if chunk_id:
                    add_file_command += [ '--chunks', chunk_id ]

                add_file_command += [src, dst, gp4_file]

                if call_process('.', add_file_command) != 0:
                    return False

            if not file_is_renamed:
                known_paths[key] = dst

        if gp4_contents is not None:
            with open(gp4_file, 'w') as f:
                f.writelines(gp4_contents)

    return True

#-------------------------------------------------------------------------------
def ps4_generate_pkgs(env, loose_files_dir, destination):
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
        pkg_file = env.format(os.path.join(destination, package['pkg_dest']), **package)
        dest_dir = os.path.dirname(pkg_file)
        print(dest_dir)
        safe_makedirs(dest_dir)

        if call_process(dest_dir,
                        ["orbis-pub-cmd.exe", "img_create", gp4_file, pkg_file],
                        heartbeat = 30) != 0:
            return False

        # Verify package but do not fail job if the verification fails
        call_process(dest_dir, [ "orbis-pub-cmd", "img_verify", "--passcode", package['passcode'], pkg_file ])

    return True

