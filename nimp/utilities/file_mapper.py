# -*- coding: utf-8 -*-

import os
import os.path
import fnmatch
import shutil
import time
import functools
import itertools
import pathlib

from nimp.utilities.logging import *
from nimp.utilities.paths   import *

#-------------------------------------------------------------------------------
def map_sources(handler, format_args = {}):
    """ Use this to execute a single argument function on the sources of the mapped
        files.
    """
    def _source_mapper(source, *args):
        yield handler(source)
    return FileMapper(mapper = _source_mapper,  format_args = format_args)

#-------------------------------------------------------------------------------
def map_copy(handler, format_args = {}):
    """ To execute 2-arity function of the mapped files.
    """
    def _copy_mapper(source, *args):
        yield handler(source)
    return FileMapper(mapper = _copy_mapper,  format_args = format_args)

#-------------------------------------------------------------------------------
def robocopy_mapper(source, destination):
    """ 'Robust' copy mapper. """
    log_verbose("{0} => {1}", source, destination)
    if os.path.isdir(source) and not os.path.exists(destination):
        os.makedirs(destination)
    else:
        dest_dir = os.path.dirname(destination)
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        try:
            if os.path.exists(destination):
                os.chmod( destination, stat.S_IWRITE )
            shutil.copy(source, destination)
        except:
            log_verbose("Error running shutil.copy2 {0} {1}, trying by deleting destination file first", source, destination)
            os.remove(destination)
            shutil.copy(source, destination)
    yield True

def _default_mapper(*args):
    yield args

class FileMapper(object):
    """ TODO : Eventuellement utiliser les PurePath, de python 3.4, qui simplifieraient
        quelque trucs, nottament dans les globs.
    """
    #---------------------------------------------------------------------------
    def __init__(self, mapper = _default_mapper, format_args = {}, source_path = None, next = None):
        super(FileMapper, self).__init__()
        if source_path is None:
            if next is not None:
                source_path = next._source_path
            else:
                source_path = ''

        self._mapper        = mapper
        self._format_args   = format_args
        self._source_path   = os.path.normpath(source_path)
        self._next          = next

    #---------------------------------------------------------------------------
    def __call__(self, *args):
        if len(args) == 0:
            args = ('.')
        result          = []
        source_path_len = len(split_path(self._source_path))
        for glob_path in args:
            glob_path = self._format(glob_path)
            glob_path = os.path.join(self._source_path, glob_path)
            for source in pathlib.Path(".").glob(glob_path):
                source = str(source)
                # This is merely equivalent to os.path.relpath(source, self._source_path)
                # excepted it will handle globs pattern in the base path.
                source          = os.path.normpath(source)
                destination     = split_path(source)[source_path_len:]
                destination     = os.path.normpath('/'.join(destination))
                node            = self
                mapped_files    = [(source, destination)]
                while node is not None:
                    mapped_files = itertools.chain.from_iterable(itertools.starmap(node._mapper, mapped_files))
                    assert(mapped_files is not None)
                    node         = node._next
                result.extend(mapped_files)
        return result

    #---------------------------------------------------------------------------
    def override(self, **format_args):
        """ Inserts a node adding or overriding given format arguments.
        """
        return FileMapper(format_args = format_args, next = self)

    #---------------------------------------------------------------------------
    def exclude(self, *patterns):
        """ Ignore source paths maching one of patterns
        """
        def _exclude_mapper(source, *args):
            for pattern in patterns:
                if fnmatch.fnmatch(source, pattern):
                    raise StopIteration()
            yield (source,) + args
        return FileMapper(mapper = _exclude_mapper, source_path = self._source_path, next = self)

    #---------------------------------------------------------------------------
    def files(self):
        """ Discards directories from processed paths
        """
        def _files_mapper(source, *args):
            if os.path.isfile(source):
                yield (source,) + args
        return FileMapper(mapper = _files_mapper, source_path = self._source_path, next = self)

    #---------------------------------------------------------------------------
    def frm(self, source):
        """ Prepends 'source' to path given to subsequent calls.
        """
        source = os.path.join(self._source_path, self._format(source))
        return FileMapper(source_path = source, next = self)

    #---------------------------------------------------------------------------
    def once(self):
        """ Stores processed files and don't process them if they already have been.
        """
        processed_files = set()
        def _once_mapper(source, *args):
            if not source in processed_files:
                processed_files.add(source)
                yield (source,) + args
        return FileMapper(mapper = _once_mapper, source_path = self._source_path, next = self)
    #---------------------------------------------------------------------------
    def newer(self):
        """ Ignore files when source is newer than destination.
        """
        def _newer_mapper(source, destination, *args):
            if not os.path.exists(destination):
                yield (source, destination) + args
            elif os.path.getmtime(source) > os.path.getmtime(destination):
                yield (source, destination) + args

        return FileMapper(mapper = _newer_mapper, source_path = self._source_path, next = self)

    #---------------------------------------------------------------------------
    def recursive(self):
        """ Recurvively list all children of processed source if it is a
            directory.
        """
        def _recursive_mapper(source, destination, *args):
            yield (source, destination) + args
            if os.path.isdir(source):
                for file in os.listdir(source):
                    child_source = os.path.normpath(os.path.join(source,  file))
                    child_dest   = os.path.normpath(os.path.join(destination, file))
                    for child_source, child_destination in _recursive_mapper(child_source, child_dest):
                        yield (child_source, child_destination) + args
        return FileMapper(mapper = _recursive_mapper, source_path = self._source_path, next = self)

    #---------------------------------------------------------------------------
    def to(self, to_destination):
        """ Inserts a nodes prepending given 'to_destination' to each destination
            path processed.
        """
        to_destination = self._format(to_destination)
        def _to_mapper(source, destination = '', *args):
            destination = os.path.join(to_destination, destination)
            yield (source, destination) + args
        return FileMapper(mapper = _to_mapper, source_path = self._source_path, next = self)

    #---------------------------------------------------------------------------
    def _format(self, str):
        """ Formats given string using format arguments defined on all the
            nodes of the list.
        """
        kwargs = self._merge_format_args({})
        return str.format(**kwargs)

    #---------------------------------------------------------------------------
    def _merge_format_args(self, args):
        """ Aggregates the node's format arguments bottom-up. (Last overrided
            argument wins).
        """
        if self._next is not None:
            self._next._merge_format_args(args)
        args.update(self._format_args)
        return args

    #---------------------------------------------------------------------------
    def __getattr__(self, name):
        """ Usefull to simply retrieve format arguments, in config files for example.
        """
        if name in self._format_args:
            return self._format_args[name]
        elif self._next is not None:
            return getattr(self._next, name)
        raise AttributeError(name)
