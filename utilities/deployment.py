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

from utilities.perforce     import *
from utilities.files        import *

#-------------------------------------------------------------------------------
def publish(context, publish_callback, destination_format, **kwargs):
    destination = context.format(destination_format)
    publisher   = _FilePublisher(destination, context, **kwargs)
    if publish_callback(publisher):
        publisher.execute()
        return True
    return False

#-------------------------------------------------------------------------------
def deploy(context, source_format, ignore_globs = [], destination = ".", **kwargs):
    """ Copy the content of the given source directory, checkouting local files
        if necesseray
    """
    ignore_globs = list(ignore_globs)
    for i in range(0, len(ignore_globs)):
        ignore_globs[i] = context.format(ignore_globs[i])
        ignore_globs[i] = os.path.normpath(ignore_globs[i])

    source = context.format(source_format, **kwargs)
    log_notification("Deploying {0} locally", source)

    if not os.path.exists(source):
        log_error("{0} directory was not found, can't deploy", source)
        return False

    files_to_copy = []
    for root, directories, files in os.walk(source, topdown=False):
        for file in files:
            source_file      = os.path.join(root, file)
            target_directory = os.path.relpath(root, source)
            target_file      = os.path.join(destination, target_directory, file)
            files_to_copy.append((source_file, target_directory, target_file))

    def file_name_formatter(tuple):
        return tuple[2]

    ignored_files = 0
    with PerforceTransaction("Nimp Deployment", reconcile = False, revert_unchanged = False) as transaction:
        progress = log_progress(files_to_copy, step_name_formatter = file_name_formatter)
        for source_file, target_directory, target_file in progress:
            ignored = False
            normalized_path = os.path.normpath(target_file)
            for ignore_glob in ignore_globs:
                if fnmatch.fnmatch(normalized_path, ignore_glob):
                    log_notification("Ignoring file {0}", target_file)
                    ignored_files += 1
                    ignored = True
                    break
            if ignored:
                continue

            if not os.path.exists(target_directory):
                mkdir(target_directory)

            transaction.add(target_file)

            if os.path.exists(target_file):
                os.chmod(target_file, stat.S_IWRITE)

            shutil.copy(source_file, target_file)

    log_notification("Copied {0}/{1} files ({2} files ignored)",
                     len(files_to_copy) - ignored_files,
                     len(files_to_copy),
                     ignored_files)
    return True

#---------------------------------------------------------------------------
def get_latest_available_revision(version_directory_format, platforms, start_revision, **kwargs):
    platforms_revisions = {}
    all_revisions       = []

    for platform in platforms:
        platforms_revisions[platform] = []

        kwargs['revision'] = '*'
        kwargs['platform'] = platform
        version_directory_format = version_directory_format.replace('\\', '/')
        version_directories_glob = version_directory_format.format(**kwargs)

        for version_directory in glob.glob(version_directories_glob):
            kwargs['revision'] = '([0-9]*)'
            version_directory  = version_directory.replace('\\', '/')

            version_regex      = version_directory_format.format(**kwargs)

            version_match = re.match(version_regex, version_directory)
            version_cl    = version_match.group(1)

            platforms_revisions[platform].append(version_cl)
            all_revisions.append(version_cl)
            pass

    all_revisions.sort(reverse=True)

    for revision in all_revisions:
        available_for_all_platforms = True
        for platform in platforms:
            if not revision in platforms_revisions[platform]:
                available_for_all_platforms = False
                break
        if available_for_all_platforms and (start_revision is None or revision <= start_revision):
            return revision

    return None

#------------------------------------------------------------------------------
def deploy_latest_revision(context, directory_format, start_revision, platforms):
    latest_revision  = context.call(get_latest_available_revision,
                                    directory_format,
                                    platforms       = platforms,
                                    start_revision  =  start_revision)

    if latest_revision is None:
        log_error("No available revision found.")
        return None

    log_notification("Deploying revision {0}.", latest_revision)

    for platform in platforms:
        if not deploy(context, directory_format, revision = latest_revision, platform = platform):
            log_error("Unable to deploy revision for platform %s." % platform)
            return None

    return latest_revision

#------------------------------------------------------------------------------
def upload_microsoft_symbols(context, paths):
    symbol_files = []
    for path in paths:
        symbol_files += list_files_matching(path, ["*.pdb", "*.xdb"])

    index_content = ""

    for symbol_file in symbol_files:
        index_content += os.path.abspath(symbol_file) + "\n"

    if not write_file_content("symbols_index.txt", index_content):
        log_error("w00t ! Unable to write symbols index file.")
        return False

    result = True
    if not call_process(".",
                        [ "C:/Program Files (x86)/Windows Kits/8.1/Debuggers/x64/symstore.exe",
                          "add",
                          "/r", "/f",  "@symbols_index.txt",
                          "/s", context.symbol_server,
                          "/compress",
                          "/o",
                          "/t", "{0}_{1}_{2}".format(context.project, context.platform, context.configuration),
                          "/v", context.revision ]):
        result = False
        log_error("w00t ! An error occured while uploading symbols.")

    os.remove("symbols_index.txt")

    return result

#------------------------------------------------------------------------------
class _FilePublisher(object):
    def __init__(self, destination, parent, **override_args):
        self.destination = destination
        self._parent     = parent
        for key in override_args:
            setattr(self, key, override_args[key])
        self._files_to_copy = []

    def __getattr__(self, name):
        try:
            return object.__getattr__(self, name)
        except AttributeError:
            return getattr(self._parent, name)

    def delete_destination(self):
        def _onerror(func, path, exc_info):
            if not os.access(path, os.W_OK):
                os.chmod(path, stat.S_IWUSR)
                func(path)
            else:
                raise
        if os.path.exists(self.destination):
            shutil.rmtree(self.destination, onerror = _onerror)

    def _format(self, str, is_source = True):
        format_args     = {}
        contextes       = []
        current_context = self

        while hasattr(current_context, '_parent'):
            contextes.append(current_context)
            current_context = current_context._parent

        contextes.append(current_context)
        contextes.reverse()

        for context in contextes:
            format_args.update(**(vars(context).copy()))

        return str.format(**format_args)

    def add(self, source, include = ['*'], exclude = [], recursive = True):
        for i in range(0, len(include)):
            include[i] = self._format(include[i])
        for i in range(0, len(exclude)):
            exclude[i] = self._format(exclude[i])

        source = self._format(source)
        for source_file in list_files_matching(source, include, exclude, recursive):
            target_file = os.path.join(self.destination, source_file)
            self._files_to_copy.append((source_file, target_file))

    def execute(self):
        def file_formatter(file_tuple):
            return file_tuple[1]

        for source, target in log_progress(self._files_to_copy, step_name_formatter = file_formatter):
            target_directory    = os.path.dirname(target)

            if not os.path.isdir(target_directory):
                os.makedirs(target_directory)

            shutil.copy(source, target)
        log_notification("Deployed {0} files", len(self._files_to_copy))

