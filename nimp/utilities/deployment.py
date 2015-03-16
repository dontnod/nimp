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

from nimp.utilities.perforce     import *
from nimp.utilities.file_mapper  import *

#---------------------------------------------------------------------------
def get_latest_available_revision(context, version_directory_format, start_revision, **override_args):
    revisions                   = []
    format_args                 = vars(context).copy()
    format_args.update(override_args)
    format_args['revision']     = '*'
    version_directory_format    = version_directory_format.replace('\\', '/')
    version_directories_glob    = version_directory_format.format(**format_args)

    for version_directory in glob.glob(version_directories_glob):
        format_args['revision'] = '([0-9]*)'
        version_directory       = version_directory.replace('\\', '/')
        version_regex           = version_directory_format.format(**format_args)

        version_match = re.match(version_regex, version_directory)

        if version_match is not None:
            version_cl    = version_match.group(1)
            revisions.append(version_cl)

    revisions.sort(reverse=True)

    for revision in revisions:
        if start_revision is None or revision <= start_revision:
            return revision

    return None

#----------------------------------------------------------------------------
@contextlib.contextmanager
def deploy_latest_revision(context, version_directory_format, revision, platforms):
    for platform in platforms:
        revision = get_latest_available_revision(context, version_directory_format, revision, platform = platform)
        if revision is None:
            raise Exception("Unable to find a suitable revision for platform %s" % platform)

    files_to_deploy = context.map_files()
    for platform in platforms:
        files_to_deploy.override(revision = revision, platform = platform).src(context.cis_version_directory).recursive().files()

    with p4_transaction("Automatic Checkout",
                        revert_unchanged        = False,
                        submit_on_success       = False,
                        add_not_versioned_files = False) as transaction:
        if not all_map(checkout_and_copy(transaction), files_to_deploy()):
            raise Exception("Error while deploying %s binaries" % platform)
        yield

#------------------------------------------------------------------------------
def upload_microsoft_symbols(context, paths):
    symbols = context.map_files()

    for path in paths:
        symbols.src(path).glob("**/*.pdb", "**/*.xdb")

    with open("symbols_index.txt", "w") as symbols_index:
        for src, dest in symbols():
            symbols_index.write(src + "\n")

    result = True
    if call_process(".",
                    [ "C:/Program Files (x86)/Windows Kits/8.1/Debuggers/x64/symstore.exe",
                      "add",
                      "/r", "/f",  "@symbols_index.txt",
                      "/s", context.symbol_server,
                      "/compress",
                      "/o",
                      "/t", "{0}_{1}_{2}".format(context.project, context.platform, context.configuration),
                      "/v", context.revision ]) != 0:
        result = False
        log_error("w00t ! An error occured while uploading symbols.")

    os.remove("symbols_index.txt")

    return result

#-------------------------------------------------------------------------------
def robocopy(source, destination, *args):
    """ 'Robust' copy. """
    log_verbose("{0} => {1}", source, destination)
    if os.path.isdir(source) and not os.path.exists(destination):
        os.makedirs(destination)
    elif os.path.isfile(source):
        dest_dir = os.path.dirname(destination)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        try:
            if os.path.exists(destination):
                os.chmod(destination, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            shutil.copy(source, destination)
        except:
            return False
    return True

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
