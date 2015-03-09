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
        version_cl    = version_match.group(1)

        revisions.append(version_cl)

    revisions.sort(reverse=True)

    for revision in revisions:
        if start_revision is None or revision <= start_revision:
            return revision

    return None

#-------------------------------------------------------------------------------
def _robocopy_mapper(source, destination):
    """ 'Robust' copy mapper. """
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
            log_verbose("Error running shutil.copy2 {0} {1}, trying by deleting destination file first", source, destination)
            os.remove(destination)
            shutil.copy(source, destination)
    yield True

#-------------------------------------------------------------------------------
def robocopy(context):
    return FileMapper(_robocopy_mapper, vars(context))

#-------------------------------------------------------------------------------
def checkout(context, transaction):
    def _checkout_mapper(source, *args):
        if os.path.isfile(source) and not transaction.add(source):
            yield False

    return FileMapper(_checkout_mapper, vars(context))

#-------------------------------------------------------------------------------
def checkout_and_copy(context, transaction):
    def _checkout_and_copy_mapper(source, destination):
        if os.path.isfile(destination) and not transaction.add(destination):
            yield False
        for result in _robocopy_mapper(source, destination):
            yield result

    return FileMapper(_checkout_and_copy_mapper, vars(context))

#----------------------------------------------------------------------------
@contextlib.contextmanager
def deploy_latest_revision(context, version_directory_format, revision, platforms):
    for platform in platforms:
        revision = get_latest_available_revision(context, version_directory_format, revision, platform = platform)
        if revision is None:
            raise Exception("Unable to find a suitable revision for platform %s" % platform)

    with p4_transaction("Automatic Checkout",
                        revert_unchanged = False,
                        add_not_versioned_files = False) as transaction:
        transaction.abort()
        for platform in platforms:
            deploy_binaries = checkout_and_copy(context, transaction).files().recursive().override(revision  = revision)
            deploy_binaries = deploy_binaries.override(platform = platform)
            deploy_binaries = deploy_binaries.frm(context.cis_version_directory)
            if not all(deploy_binaries()):
                raise Exception("Error while deploying %s binaries" % platform)
        yield

#------------------------------------------------------------------------------
def upload_microsoft_symbols(context, paths):
    write_symbol_index = map_sources(lambda file: symbols_index.write(file + "\n"))

    with open("symbols_index.txt", "w") as symbols_index:
        for path in paths:
            if not all(write_symbol_index.frm(path)("**/*.pdb", "**/*.xdb")):
                return False

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
