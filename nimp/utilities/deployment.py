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

from nimp.utilities.perforce import *
from nimp.utilities.file_mapper import *
from nimp.utilities.hashing import *

#---------------------------------------------------------------------------
def get_latest_available_revision(env, version_directory_format, max_revision, **override_args):
    revisions = []
    format_args = vars(env).copy()
    format_args.update(override_args)
    format_args['revision']  = '*'
    version_directory_format = version_directory_format.replace('\\', '/')
    version_directories_glob = version_directory_format.format(**format_args)

    for version_directory in glob.glob(version_directories_glob):
        format_args['revision'] = '(\d+)'
        version_directory       = version_directory.replace('\\', '/')
        version_regex           = version_directory_format.format(**format_args)

        version_match = re.match(version_regex, version_directory)

        if version_match is not None:
            version_cl = version_match.group(1)
            revisions.append(version_cl)

    revisions.sort(reverse=True)

    for revision in revisions:
        if max_revision is None or int(revision) <= int(max_revision):
            return revision

    raise Exception('No revision <= %s in %s. Candidates are: %s' % (max_revision, version_directories_glob, ' '.join(revisions)))

#----------------------------------------------------------------------------
@contextlib.contextmanager
def deploy_latest_revision(env, version_directory_format, revision, platforms):

    # Check that there is a revision for each platform
    for platform in platforms:
        revision = get_latest_available_revision(env, version_directory_format,
                                                 revision, platform = platform)

    files_to_deploy = env.map_files()
    if(hasattr(env, 'deploy_version_root')):
        files_to_deploy = files_to_deploy.to(env.deploy_version_root)
    for platform in platforms:
        files_to_deploy.override(revision = revision, platform = platform).src(env.publish_version).recursive().files()

    import nimp.utilities.file_mapper as file_mapper
    with p4_transaction("Automatic Checkout",
                        revert_unchanged = False,
                        submit_on_success = False,
                        add_not_versioned_files = False) as transaction:
        if not file_mapper.all_map(checkout_and_copy(transaction), files_to_deploy()):
            raise Exception("Error while deploying %s binaries" % platform)
        yield

#------------------------------------------------------------------------------
def upload_symbols(env, symbols):

    result = True

    if env.is_microsoft_platform:
        with open("symbols_index.txt", "w") as symbols_index:
            for src, dest in symbols:
                symbols_index.write(src + "\n")

        if call_process(".",
                        [ "C:/Program Files (x86)/Windows Kits/8.1/Debuggers/x64/symstore.exe",
                          "add",
                          "/r", "/f", "@symbols_index.txt",
                          "/s", env.format(env.publish_symbols),
                          "/compress",
                          "/o",
                          "/t", "{0}_{1}_{2}".format(env.project, env.platform, env.configuration),
                          "/v", env.revision ]) != 0:
            result = False
            log_error(log_prefix() + "Oops! An error occurred while uploading symbols.")

        os.remove("symbols_index.txt")

    return result

#-------------------------------------------------------------------------------
def robocopy(src, dest):
    """ 'Robust' copy. """

    # If these look like a Windows path, get rid of all "/" path separators
    if os.sep is '\\':
        src = src.replace('/', '\\')
        dest = dest.replace('/', '\\')
    elif os.sep is '/':
        src = src.replace('\\', '/')
        dest = dest.replace('\\', '/')

    log_verbose(log_prefix() + 'Copying “{0}” to “{1}”', src, dest)

    if os.path.isdir(src):
        safe_makedirs(dest)
    elif os.path.isfile(src):
        dest_dir = os.path.dirname(dest)
        safe_makedirs(dest_dir)
        try:
            if os.path.exists(dest):
                os.chmod(dest, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            shutil.copy2(src, dest)
        except Exception as e:
            log_error(log_prefix() + 'Error: {0}', e)
            return False
    else:
        log_error(log_prefix() + 'Error: not such file or directory “{0}”', src)
        return False

    return True

#-------------------------------------------------------------------------------
def force_delete(file):
    """ 'Robust' delete. """
    if os.path.exists(file):
        os.chmod(file, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.remove(file)

#-------------------------------------------------------------------------------
def checkout(transaction):
    def _checkout_mapper(src, dest):
        if src is None:
            return True
        if os.path.isfile(src) and not transaction.add(src):
            return False
        return True

    return _checkout_mapper

#-------------------------------------------------------------------------------
def checkout_and_copy(transaction):
    def _checkout_and_copy_mapper(src, dest):
        if dest is None:
            raise Exception("checkout_and_copy() called on empty destination")
        if os.path.isfile(dest) and not transaction.add(dest):
            return False
        if not robocopy(src, dest):
            return False
        return True

    return _checkout_and_copy_mapper

