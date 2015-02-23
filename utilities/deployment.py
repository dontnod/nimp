# -*- coding: utf-8 -*-

from datetime import date

import os
import stat
import os.path
import tempfile;
import shutil
import stat
import glob
import re

from utilities.perforce     import *
from utilities.files        import *

#-------------------------------------------------------------------------------
def publish(context, publish_callback, destination_format, **kwargs):
    destination = context.format(destination_format)
    publisher   = _FilePublisher(destination, context, **kwargs)
    return publish_callback(publisher)

#-------------------------------------------------------------------------------
def deploy(context, source_format, ignore_files = [], **kwargs):
    """ Copy the content of the given source directory, checkouting local files
        if necesseray
    """
    normalized_ignore_files = []

    for ignored_file in ignore_files:
        normalized_ignore_files.append(os.path.normpath(ignored_file).lower())

    source = context.format(source_format, **kwargs)
    log_notification("Deploying {0} locally", source)

    if not os.path.exists(source):
        log_error("{0} directory was not found, can't deploy", source)
        return False

    with PerforceTransaction("Binaries checkout", reconcile = False) as transaction:
        for root, directories, files in os.walk(source, topdown=False):
            for file in files:
                source_file     = os.path.join(root, file)
                local_directory = os.path.relpath(root, source)
                local_file      = os.path.join('.', local_directory, file)

                if os.path.normpath(local_file).lower() in normalized_ignore_files:
                    log_verbose("Ignoring file {0}", local_file)
                    continue

                log_verbose("{0} => {1}", source_file, local_file)

                if not os.path.exists(local_directory):
                    mkdir(local_directory)

                transaction.add(local_file)

                if os.path.exists(local_file):
                    os.chmod(local_file, stat.S_IWRITE)
                shutil.copy(source_file, local_file)
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
class _FilePublisher(object):
    def __init__(self, destination, parent, **override_args):
        self.destination = destination
        self._parent     = parent
        for key in override_args:
            setattr(self, key, override_args[key])

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
        format_args = {}
        contextes = []
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
        if os.path.isfile(source):
            target              = os.path.join(self.destination, os.path.relpath(source, '.'))
            target_directory    = os.path.dirname(target)

            if not os.path.exists(target_directory):
                os.makedirs(target_directory)

            log_verbose("{0} => {1}", source, target)
            shutil.copy(source, target)
            os.chmod(target, stat.S_IWUSR)
        else:
            def _copy_callback(source, destination):
                os.chmod(destination, stat.S_IWUSR)
            if recursive:
                recursive_glob_copy(source, self.destination, include, exclude, copy_callback = _copy_callback)
            else:
                glob_copy(source, self.destination, include, exclude, copy_callback = _copy_callback)
