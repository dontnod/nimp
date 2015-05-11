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
def get_latest_available_revision(env, version_directory_format, start_revision, **override_args):
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
        if start_revision is None or revision <= start_revision:
            return revision

    return None

#----------------------------------------------------------------------------
@contextlib.contextmanager
def deploy_latest_revision(env, version_directory_format, revision, platforms):
    for platform in platforms:
        revision = get_latest_available_revision(env, version_directory_format, revision, platform = platform)
        if revision is None:
            raise Exception("Unable to find a suitable revision for platform %s" % platform)

    files_to_deploy = env.map_files()
    for platform in platforms:
        files_to_deploy.override(revision = revision, platform = platform).src(env.cis_version_directory).recursive().files()

    with p4_transaction("Automatic Checkout",
                        revert_unchanged = False,
                        submit_on_success = False,
                        add_not_versioned_files = False) as transaction:
        if not all_map(checkout_and_copy(transaction), files_to_deploy()):
            raise Exception("Error while deploying %s binaries" % platform)
        yield

#------------------------------------------------------------------------------
def upload_microsoft_symbols(env, paths):
    symbols = env.map_files()

    for path in paths:
        symbols.src(path).glob("**/*.pdb", "**/*.xdb")

    with open("symbols_index.txt", "w") as symbols_index:
        for src, dest in symbols():
            symbols_index.write(src + "\n")

    result = True
    if call_process(".",
                    [ "C:/Program Files (x86)/Windows Kits/8.1/Debuggers/x64/symstore.exe",
                      "add",
                      "/r", "/f", "@symbols_index.txt",
                      "/s", env.symbol_server,
                      "/compress",
                      "/o",
                      "/t", "{0}_{1}_{2}".format(env.project, env.platform, env.configuration),
                      "/v", env.revision ]) != 0:
        result = False
        log_error("Oops! An error occurred while uploading symbols.")

    os.remove("symbols_index.txt")

    return result

#-------------------------------------------------------------------------------
def robocopy(source, destination, *args):
    """ 'Robust' copy. """
    log_verbose("{0} => {1}", source, destination)
    if os.path.isdir(source):
        safe_makedirs(destination)
    elif os.path.isfile(source):
        dest_dir = os.path.dirname(destination)
        safe_makedirs(dest_dir)
        try:
            if os.path.exists(destination):
                os.chmod(destination, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            shutil.copy2(source, destination)
        except:
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
    def _checkout_mapper(source, *args):
        if os.path.isfile(source) and not transaction.add(source):
            return False
        return True
    return _checkout_mapper

#-------------------------------------------------------------------------------
def checkout_and_copy(transaction):
    def _checkout_and_copy_mapper(source, destination, *args):
        if os.path.isfile(destination) and not transaction.add(destination):
            return False
        if not robocopy(source, destination):
            return False
        return True
    return _checkout_and_copy_mapper

#-----------------------------------------------------------------------------
def generate_toc(file):
    def _generate_toc_mapper(src, *args):
        file, ext = os.path.splitext(src)
        uncompressed_size_file = '{0}.uncompressed_size'.format(file)
        uncompressed_size = 0
        if os.path.isfile(uncompressed_size):
            with open(uncompressed_size_file, 'r') as uncompressed_size_file:
                uncompressed_size = uncompressed_size_file.read()
        size = os.path.getsize(src)
        md5 = get_file_md5(src)
        file.write('{0} {1} {2} {3}', size, uncompressed_size, src, md5)
    return _generate_toc_mapper

