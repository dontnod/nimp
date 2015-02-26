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

from utilities.perforce     import *
from utilities.files        import *

#---------------------------------------------------------------------------
class _DecoratorBase(object):
    def __init__(self, transaction):
        object.__init__(transaction)
        self.transaction = transaction

    def __getattr__(self, name):
        if name == "relative":
            return relative
        elif name == "ignore":
            return ignore

        return getattr(self.transaction, name)

    #------------------------------------------------------------------------------
    def relative(self, path):
        return _RelativeDecorator(self, path)

    #------------------------------------------------------------------------------
    def ignore_added_files(self):
        return _IgnoreDecorator(self)

#------------------------------------------------------------------------------
class CopyTransaction(_DecoratorBase):
    def __init__(self,
                 parent,
                 destination       = ".",
                 checkout          = False,
                 overwrite         = True,
                 **override_args):
        _DecoratorBase.__init__(self, self)
        self.destination      = destination
        self._parent          = parent
        self._checkout        = checkout
        self._overwrite       = overwrite
        self._files_to_copy   = []
        self._ignored_files   = []

        for key in override_args:
            setattr(self, key, override_args[key])

    #---------------------------------------------------------------------------
    def __getattr__(self, name):
        try:
            return object.__getattr__(self, name)
        except AttributeError:
            return getattr(self._parent, name)

    #---------------------------------------------------------------------------
    def override(**kwargs):
        result = CopyTransaction(self, self.destination, **kwargs)
        result._files_to_copy = self._files_to_copy
        return result

    #---------------------------------------------------------------------------
    def delete_destination(self):
        def _onerror(func, path, exc_info):
            if not os.access(path, os.W_OK):
                os.chmod(path, stat.S_IWUSR)
                func(path)
            else:
                raise
        if os.path.exists(self.destination):
            shutil.rmtree(self.destination, onerror = _onerror)

    #---------------------------------------------------------------------------
    def add(self, *args, include = ['*'], exclude = [], relocate = None, capitalize = False, recursive = True):
        files_to_add = self._enumerate_files(*args,
                                             include    = include,
                                             exclude    = exclude,
                                             relocate   = relocate,
                                             capitalize = capitalize,
                                             recursive  = recursive)
        self._files_to_copy.extend(files_to_add)

    def ignore(self, *args, include = ['*'], exclude = [], relocate = None, capitalize = False, recursive = True):
        for file in self._enumerate_files(*args,
                                          include    = include,
                                          exclude    = exclude,
                                          relocate   = relocate,
                                          capitalize = capitalize,
                                          recursive  = recursive):
            self._ignored_files.append(file[0])

    def _enumerate_files(self, *args, include = ['*'], exclude = [], relocate = None, capitalize = False, recursive = True):
        for source in args:
            for i in range(0, len(include)):
                include[i] = self._format(include[i])
            for i in range(0, len(exclude)):
                exclude[i] = self._format(exclude[i])

            source = self._format(source)

            for source_file in list_files_matching(source, include, exclude, recursive):
                target_file = os.path.join(self.destination, source_file)

                if os.path.isdir(source):
                    source_file = os.path.join(source, source_file)

                if relocate is not None:
                    target_file = os.path.relpath(target_file, relocate[0])
                    target_file = os.path.join(relocate[1], target_file)

                if capitalize:
                    target_file = target_file.upper()

                yield (source_file, target_file)

    #---------------------------------------------------------------------------
    def add_latest_revision(self, source_format, start_revision):
        latest_revision  = get_latest_available_revision(source_format, start_revision, **(var(self).copy()))

        if latest_revision is None:
            log_error("No available revision found.")
            return None

        log_notification("Found revision {0}.", latest_revision)
        for platform in platforms:
            child = self.override_context(revision = latest_revision, platform = platform)
            child.add(destination)

        return latest_revision

    #---------------------------------------------------------------------------
    def do(self):
        if(self._checkout):
            with PerforceTransaction("Automatic File Deployment", reconcile = False, revert_unchanged = False) as transaction:
                for source, target in self._files_to_copy:
                    transaction.add(target)
                return self._copy_files()
        else:
            return self._copy_files()

    #---------------------------------------------------------------------------
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

    #---------------------------------------------------------------------------
    def _copy_files(self):
        def file_formatter(file_tuple):
            return file_tuple[1]

        self._ignored_files = [os.path.normpath(file) for file in self._ignored_files]
        for source, target in log_progress(self._files_to_copy, step_name_formatter = file_formatter):
            if os.path.normpath(source) in self._ignored_files:
                log_notification("Ignoring file {0}.", target)
                continue

            target_directory    = os.path.dirname(target)

            if not os.path.isdir(target_directory):
                os.makedirs(target_directory)

            if os.path.exists(target):
                if not self._overwrite:
                    log_notification("Ignoring existing file {0}.", target)
                    continue
                os.chmod(target, stat.S_IWRITE)

            shutil.copy(source, target)

        log_notification("Copied {0} files", len(self._files_to_copy))
        return True

class _CheckoutDecorator(_DecoratorBase):
    def __init__(self, transaction):
        _DecoratorBase.__init__(self, transaction)
        self._transaction = transaction

    def add(self, *args, **kwargs):
        self.transaction.ignore(*args, **kwargs)

    def ignore(self, *args, **kwargs):
        self.transaction.add(*args, **kwargs)

#---------------------------------------------------------------------------
class _IgnoreDecorator(_DecoratorBase):
    def __init__(self, transaction):
        _DecoratorBase.__init__(self, transaction)
        self._transaction = transaction

    def add(self, *args, **kwargs):
        self.transaction.ignore(*args, **kwargs)

    def ignore(self, *args, **kwargs):
        self.transaction.add(*args, **kwargs)

#---------------------------------------------------------------------------
class _RelativeDecorator(_DecoratorBase):
    def __init__(self, transaction, relative_source):
        _DecoratorBase.__init__(self, transaction)
        self._relative_source   = relative_source

    def add(self, *args, **kwargs):
        relative_sources = [os.path.join(self._relative_source, source) for source in args]
        self.transaction.add(*relative_sources, **kwargs)

    def ignore(self, *args, **kwargs):
        relative_sources = [os.path.join(self._relative_source, source) for source in args]
        self.transaction.ignore(*relative_sources, **kwargs)

#---------------------------------------------------------------------------
def get_latest_available_revision(version_directory_format, start_revision, **kwargs):
    revisions                   = []
    kwargs['revision']          = '*'
    version_directory_format    = version_directory_format.replace('\\', '/')
    version_directories_glob    = version_directory_format.format(**kwargs)

    for version_directory in glob.glob(version_directories_glob):
        kwargs['revision'] = '([0-9]*)'
        version_directory  = version_directory.replace('\\', '/')
        version_regex      = version_directory_format.format(**kwargs)

        version_match = re.match(version_regex, version_directory)
        version_cl    = version_match.group(1)

        revisions.append(version_cl)

    revisions.sort(reverse=True)

    for revision in revisions:
        if start_revision is None or revision <= start_revision:
            return revision

    return None

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
