# -*- coding: utf-8 -*-

import os
import os.path
import fnmatch
import shutil
import time
import functools
import glob2
import itertools
import pathlib
import stat
import re

from nimp.utilities.logging import *
from nimp.utilities.paths import *

#-------------------------------------------------------------------------------
def all_map(mapper, file_set):
    for args in file_set:
        if not mapper(*args):
            return False
    return True

#-------------------------------------------------------------------------------
def _default_mapper(*args):
    yield args

class FileMapper(object):
    """ TODO : Eventuellement utiliser les PurePath, de python 3.4, qui simplifieraient
        quelque trucs, nottament dans les globs.
    """
    #---------------------------------------------------------------------------
    def __init__(self, mapper = _default_mapper, format_args = {}):
        super(FileMapper, self).__init__()
        self._mapper = mapper
        self._next = []
        self._format_args = format_args

    #---------------------------------------------------------------------------
    def __call__(self, *args):
        results = self._mapper(*args)
        if len(self._next) == 0:
            for result in results:
                yield result
        else:
            for result in results:
                for next in self._next:
                    for next_result in next(*result):
                        yield next_result

    #---------------------------------------------------------------------------
    def glob(self, *patterns):
        def _glob_mapper(src = '', dst = '', *args):
            source_path_len = len(split_path(src))
            for glob_path in patterns:
                glob_path = self._format(glob_path)
                glob_path = os.path.join(src, glob_path)
                for glob_source in glob2.glob(glob_path):
                    glob_source = str(glob_source)
                    # This is merely equivalent to os.path.relpath(source, self._source_path)
                    # excepted it will handle globs pattern in the base path.
                    glob_source = os.path.normpath(glob_source)
                    destination = split_path(glob_source)[source_path_len:]
                    destination = '/'.join(destination)
                    destination = os.path.join(dst, destination)
                    destination = os.path.normpath(destination)
                    yield (glob_source, destination) + args
        return self.append(_glob_mapper)

    #--------------------------------------------------------------------------
    def append(self, mapper = _default_mapper, format_args = None):
        next = FileMapper(mapper, format_args or self._format_args)
        self._next.append(next)
        return next

    #---------------------------------------------------------------------------
    def load_set(self, set_name):
        file_name = self._format(set_name)
        if not os.path.exists(file_name) or not os.path.isfile(file_name):
            # TODO : Always hardcode this directory to avoid bloating .nimp.conf. The file_sets_directory conf variable is
            # still used in LIS repository
            if hasattr(self, "file_sets_directory"):
                file_sets_directory = self.file_sets_directory
            else:
                file_sets_directory = ".nimp/file_sets"
            file_name = os.path.join(file_sets_directory, set_name + ".txt")
            file_name = self._format(file_name)
        locals = {}
        try:
            conf = open(file_name, "rb").read()
        except Exception as exception:
            log_error("Unable to open file : {0}", exception)
            return None
        try:
            exec(compile(conf, file_name, 'exec'), None, locals)
            if not "map" in locals:
                log_error("Configuration file {0} has no function called 'map'.", file_name)
                return None
        except Exception as e:
            log_error("Unable to load file {0}: {1}", file_name, str(e))
            return None

        locals['map'](self)

    #---------------------------------------------------------------------------
    def override(self, **format):
        """ Inserts a node adding or overriding given format arguments. """
        format_args = self._format_args.copy()
        format_args.update(format)
        return self.append(format_args = format_args)

    #---------------------------------------------------------------------------
    def exclude(self, *patterns):
        """ Ignore source paths maching one of patterns
        """
        def _exclude_mapper(source = '', *args):
            for pattern in patterns:
                pattern = self._format(pattern)
                if fnmatch.fnmatch(source, pattern):
                    log_verbose("Excluding file {0}", source)
                    raise StopIteration()
            yield (source,) + args
        return self.append(_exclude_mapper)

    #---------------------------------------------------------------------------
    def files(self):
        """ Discards directories from processed paths
        """
        def _files_mapper(source = '', *args):
            if os.path.isfile(source):
                yield (source,) + args
        return self.append(_files_mapper)

    #---------------------------------------------------------------------------
    def src(self, from_src):
        """ Prepends 'source' to path given to subsequent calls.
        """
        from_src = self._format(from_src)
        def _src_mapper(source = '', *args):
            source = os.path.join(self._format(source), from_src)
            source = os.path.normpath(source)
            yield (source,) + args
        return self.append(_src_mapper)

    #---------------------------------------------------------------------------
    def once(self):
        """ Stores processed files and don't process them if they already have been.
        """
        processed_files = set()
        def _once_mapper(source, *args):
            if not source in processed_files:
                processed_files.add(source)
                yield (source,) + args

        return self.append(_once_mapper)

    #---------------------------------------------------------------------------
    def newer(self):
        """ Ignore files when source is newer than destination.
        """
        def _newer_mapper(source, destination, *args):
            if not os.path.exists(destination):
                yield (source, destination) + args
            elif os.path.getmtime(source) > os.path.getmtime(destination):
                yield (source, destination) + args

        return self.append(_newer_mapper)

    #---------------------------------------------------------------------------
    def recursive(self):
        """ Recurvively list all children of processed source if it is a
            directory.
        """
        def _recursive_mapper(source, destination = '', *args):
            yield (source, destination) + args
            if os.path.isdir(source):
                for file in os.listdir(source):
                    child_source = os.path.normpath(os.path.join(source, file))
                    child_dest = os.path.normpath(os.path.join(destination, file))
                    for child_source, child_destination in _recursive_mapper(child_source, child_dest):
                        yield (child_source, child_destination) + args
        return self.append(_recursive_mapper)

    #---------------------------------------------------------------------------
    def replace(self, pattern, repl, flags = 0):
        """ Performs a re.sub on destination
        """
        pattern = self._format(pattern)
        repl = self._format(repl)
        def _replace_mapper(source, destination, *args):
            destination = re.sub(pattern, repl, destination, flags = flags)
            yield (source, destination) + args
        return self.append(_replace_mapper)

    #---------------------------------------------------------------------------
    def to(self, to_destination):
        """ Inserts a nodes prepending given 'to_destination' to each destination
            path processed.
        """
        to_destination = self._format(to_destination)
        def _to_mapper(source = '', destination = '', *args):
            destination = os.path.join(destination, to_destination)
            yield (source, destination) + args
        return self.append(_to_mapper)

    #---------------------------------------------------------------------------
    def upper(self):
        """ Yields all destination files uppercase
        """
        def _upper_mapper(source, destination, *args):
            yield (source, destination.upper()) + args
        return self.append(_upper_mapper)

    #---------------------------------------------------------------------------
    def _format(self, str):
        """ Formats given string using format arguments defined on all the
            nodes of the list.
        """
        return str.format(**self._format_args)

    #---------------------------------------------------------------------------
    def __getattr__(self, name):
        """ Usefull to simply retrieve format arguments, in config files for example.
        """
        try:
            return self._format_args[name]
        except KeyError:
            raise AttributeError(name)
