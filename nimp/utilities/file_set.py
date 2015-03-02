# -*- coding: utf-8 -*-

import os
import os.path
import fnmatch
import shutil
import time

from nimp.utilities.logging import *
from nimp.utilities.paths   import *

def list_files(context):
    return _FileListSet(vars(context))

def copy_files(context):
    return _CopyFileSet(vars(context))

def copy_newer(context, source, destination):
    files = copy_files(context).frm(source).newer().to(destination)
    files = files.recursive().add('*')
    files.process(shutil.copy)

def add_to_p4(context, transaction, path):
    files = list_files(context).frm(path).recursive().add('*').process(transaction.add)

def copy_mkdest_dir(source, destination):
    target_dir = os.path.dirname(destination)
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    shutil.copy2(source, destination)

class _FileSet(object):
    """ This class is used to enumerate and copy files with a 'fluent' syntax,
        allowing quite complex operations on paths, like including, excluding
        globs, capitalizing file names, relocationg subdirectories in target
        directory, aggregate modification dates, etc...
        For example, to copy all pdbs recreating the source arborescence in
        'source_directory' in the target directory:
        copy_set().from('/a/path/to/source/directory).to('/target_directory').recursive().add('*')(shutils.copy)
        To submit all'.bnk' except one matching 'E1*' files in a dir :
        with p4_transaction("Update wwise banks) as trans:
            copy_list().exclude('E1*').add('WwiseDir/**/*.bnk')(trans.add)
    """
    def __init__(self, add_callback, source_path = '', format_args = {}, next = None):
        super(_FileSet, self).__init__()
        self._format_args   = format_args
        self._source_path   = os.path.normpath(source_path)
        self._add_callback  = add_callback
        self._next          = next

    def add(self, *globs):
        base_path_len = len(split_path(self._source_path))
        for glob_path in globs:
            glob_path = os.path.join(self._source_path, glob_path)
            glob_path = self._format(glob_path)
            for source in glob.glob(glob_path):
                source = os.path.normpath(source)
                # It is merely equivalent to os.path.relpath(source, self._source_path)
                # excepted it will handle globs pattern in the base path.
                destination = os.path.normpath('/'.join(split_path(source)[base_path_len:]))
                self._add_callback(self, source, destination)
        return self

    def exclude(self, *patterns):
        def _exclude_add(self, source, destination):
            for pattern in patterns:
                if fnmatch.fnmatch(source, pattern):
                    return
            self._forward(source, destination)
        return self._insert(_exclude_add)

    def frm(self, source):
        source = self._format(source)
        return self._insert(source_path = os.path.join(self._source_path, source))

    def format(self, **format_args):
        return self._insert(format_args = format_args)

    def newer(self):
        def _add_newer(self, source, destination):
            if not os.path.exists(destination):
                log_verbose("Adding new file {0}", source, time.gmtime(source_mtime), time.gmtime(destination_mtime))
                self._forward(source, destination)
            else:
                source_mtime      = os.path.getmtime(source)
                destination_mtime = os.path.getmtime(destination)
                if source_mtime > destination_mtime:
                    time_format = "%d/%m/%y - %H:%M:%S"
                    source_mtime_str      = time.strftime(time_format, time.gmtime(source_mtime))
                    destination_mtime_str = time.strftime(time_format, time.gmtime(destination_mtime))
                    log_verbose("Adding newer file {0} ({1} > {2})", source, source_mtime_str, destination_mtime_str)
                    self._forward(source, destination)

        return self._insert(_add_newer)

    def recursive(self):
        def _recursive_add(self, source, destination):
            if os.path.isdir(source):
                for file in os.listdir(source):
                    child_source = os.path.normpath(os.path.join(source,  file))
                    child_dest   = os.path.normpath(os.path.join(destination, file))
                    if os.path.isdir(child_source):
                        _recursive_add(self, child_source, child_dest)
                    else:
                        self._forward(child_source, child_dest)
            else:
                self._forward(source, destination)
        return self._insert(_recursive_add)

    def to(self, to_destination):
        to_destination = self._format(to_destination)
        def _add_to(self, source, destination):
            self._forward(source, os.path.join(to_destination, destination))
        return self._insert(_add_to)

    def _format(self, str):
        kwargs = self._merge_format_args({})
        return str.format(**kwargs)

    def _forward(self, source, destination):
        self._next._add_callback(self._next, source, destination)

    def _merge_format_args(self, args):
        if self._next is not None:
            self._next._merge_format_args(args)
        args.update(self._format_args)
        return args

    def _insert(self, add_callback = _forward, source_path = None, format_args = {}):
        return _FileSet(add_callback, source_path or self._source_path, format_args, self)

    def __iter__(self):
        return self._next.__iter__()

    def process(self, *callbacks):
        return self._next.process(*callbacks)

class _FileListSet(_FileSet):
    def __init__(self, format_args):
        super(_FileListSet, self).__init__(_FileListSet.add_file, format_args = format_args)
        self.files = []

    def add_file(self, source, destination):
        if os.path.isfile(source):
            self.files.append(source)

    def __iter__(self):
        return self.files.__iter__()

    def process(self, *callbacks):
        for file in log_progress(self.files):
            for callback in callbacks:
                callback(file)

class _CopyFileSet(_FileSet):
    def __init__(self, format_args):
        super(_CopyFileSet, self).__init__(_CopyFileSet.add_file, format_args = format_args)
        self.files = []

    def add_file(self, source, destination):
        if os.path.isfile(source):
            self.files.append((source, destination))

    def __iter__(self):
        return self.files.__iter__()

    def process(self, *callbacks):
        def format_step(entry):
            return entry[1]

        for source, destination in log_progress(self.files, step_name_formatter = format_step):
            for callback in callbacks:
                callback(source, destination)