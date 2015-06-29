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
def _default_mapper(source, destination):
    yield (source, destination)


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
    def __call__(self, source = None, destination = None):
        results = self._mapper(source, destination)
        if len(self._next) == 0:
            for result in results:
                # Only test the first element because some filemappers only worry about source
                if result[0] is not None:
                    yield result
        else:
            for result in results:
                for next in self._next:
                    for next_result in next(*result):
                        yield next_result

    #---------------------------------------------------------------------------
    def glob(self, *patterns):
        def _glob_mapper(src, dst):
            if src is None:
                source_path_len = 0
            else:
                source_path_len = len(split_path(src))

            for pattern in patterns:
                found = False
                pattern = self._format(pattern)
                if src is None:
                    glob_path = pattern
                else:
                    glob_path = os.path.join(src, pattern)
                print("matching for “%s” in “%s” (aka. “%s”)" % (pattern, src, glob_path))

                for glob_source in glob2.glob(glob_path):
                    found = True
                    glob_source = str(glob_source)
                    # This is merely equivalent to os.path.relpath(source, self._source_path)
                    # excepted it will handle globs pattern in the base path.
                    glob_source = os.path.normpath(glob_source)
                    if dst is not None:
                        destination = split_path(glob_source)[source_path_len:]
                        destination = '/'.join(destination)
                        destination = os.path.join(dst, destination)
                        destination = os.path.normpath(destination)
                    else:
                        destination = None

                    yield (glob_source, destination)
                if not found:
                    raise Exception("No match for “%s” in “%s” (aka. “%s”)" % (pattern, src, glob_path))
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
            log_error(log_prefix() + "Error loading file set : unable to open file: {0}", exception)
            return None
        try:
            exec(compile(conf, file_name, 'exec'), None, locals)
            if not "map" in locals:
                log_error(log_prefix() + "Configuration file {0} has no function called 'map'.", file_name)
                return None
        except Exception as e:
            log_error(log_prefix() + "Error loading file set : unable to load file {0}: {1}", file_name, str(e))
            return None

        locals['map'](self)

        return self

    #---------------------------------------------------------------------------
    def override(self, **format):
        """ Inserts a node adding or overriding given format arguments. """
        format_args = self._format_args.copy()
        format_args.update(format)
        return self.append(format_args = format_args)

    #---------------------------------------------------------------------------
    def exclude(self, *patterns):
        return self._exclude(False, *patterns)

    #---------------------------------------------------------------------------
    def exclude_ignore_case(self, *patterns):
        return self._exclude(True, *patterns)

    #---------------------------------------------------------------------------
    def _exclude(self, ignore_case, *patterns):
        """ Ignore source paths maching one of patterns
        """
        def _exclude_mapper(source, destination):
            for pattern in patterns:
                pattern = self._format(pattern)
                if ignore_case:
                    source = source.lower()
                    pattern = pattern.lower()
                if fnmatch.fnmatch(source, pattern):
                    log_verbose(log_prefix() + "Excluding file {0}", source)
                    raise StopIteration()
            yield (source, destination)
        return self.append(_exclude_mapper)

    #---------------------------------------------------------------------------
    def files(self):
        """ Discards directories from processed paths
        """
        def _files_mapper(source, destination):
            if os.path.isfile(source):
                yield (source, destination)
        return self.append(_files_mapper)

    #---------------------------------------------------------------------------
    def src(self, from_src):
        """ Prepends 'source' to path given to subsequent calls.
        """
        from_src = self._format(from_src)
        def _src_mapper(source, destination):
            if source is None:
                source = from_src
            else:
                source = os.path.join(self._format(source), from_src)
            source = os.path.normpath(source)
            yield (source, destination)
        return self.append(_src_mapper)

    #---------------------------------------------------------------------------
    def once(self):
        """ Stores processed files and don't process them if they already have been.
        """
        processed_files = set()
        def _once_mapper(source, destination):
            if source is None:
                raise Exception("once() called on empty fileset")
            if not source in processed_files:
                processed_files.add(source)
                yield (source, destination)

        return self.append(_once_mapper)

    #---------------------------------------------------------------------------
    def newer(self):
        """ Ignore files when source is newer than destination.
        """
        def _newer_mapper(source, destination):
            if source is None or destination is None:
                raise Exception("newer() called on empty fileset")
            if not os.path.exists(destination):
                yield (source, destination)
            elif os.path.getmtime(source) > os.path.getmtime(destination):
                yield (source, destination)

        return self.append(_newer_mapper)

    #---------------------------------------------------------------------------
    def recursive(self):
        """ Recurvively list all children of processed source if it is a
            directory.
        """
        def _recursive_mapper(source, destination):
            if source is None:
                raise Exception("recursive() called on empty fileset")
            yield (source, destination)
            if os.path.isdir(source):
                for file in os.listdir(source):
                    child_source = os.path.normpath(os.path.join(source, file))
                    child_dest = os.path.normpath(os.path.join(destination, file))
                    for child_source, child_destination in _recursive_mapper(child_source, child_dest):
                        yield (child_source, child_destination)
        return self.append(_recursive_mapper)

    #---------------------------------------------------------------------------
    def replace(self, pattern, repl, flags = 0):
        """ Performs a re.sub on destination
        """
        pattern = self._format(pattern)
        repl = self._format(repl)
        def _replace_mapper(source, destination):
            if destination is None:
                raise Exception("replace() called with destination = None")
            destination = re.sub(pattern, repl, destination, flags = flags)
            yield (source, destination)
        return self.append(_replace_mapper)

    #---------------------------------------------------------------------------
    def to(self, to_destination):
        """ Inserts a nodes prepending given 'to_destination' to each destination
            path processed.
        """
        to_destination = self._format(to_destination)
        def _to_mapper(source, destination):
            if destination is None:
                destination = to_destination
            else:
                destination = os.path.join(destination, to_destination)
            yield (source, destination)
        return self.append(_to_mapper)

    #---------------------------------------------------------------------------
    def upper(self):
        """ Yields all destination files uppercase
        """
        def _upper_mapper(source, destination):
            if destination is None:
                raise Exception("upper() called with destination = None")
            yield (source, destination.upper())
        return self.append(_upper_mapper)

    #---------------------------------------------------------------------------
    def _format(self, str):
        """ Formats given string using format arguments defined on all the
            nodes of the list.
        """
        result = str.format(**self._format_args)
        result = time.strftime(result)
        return result

    #---------------------------------------------------------------------------
    def __getattr__(self, name):
        """ Usefull to simply retrieve format arguments, in config files for example.
        """
        try:
            return self._format_args[name]
        except KeyError:
            raise AttributeError(name)

