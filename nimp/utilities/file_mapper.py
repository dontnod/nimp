# -*- coding: utf-8 -*-
# Copyright (c) 2016 Dontnod Entertainment

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
''' File listing system '''

import fnmatch
import logging
import os
import os.path
import re
import time

import glob2

import nimp.utilities.system

def all_map(mapper, fileset):
    ''' Passes all the files in the given fileset and checks it returns true
        for every file '''
    for src, dest in fileset:
        if src is None:
            pass
        if not mapper(src, dest):
            return False
    return True

def _identity_mapper(src, dest):
    yield src, dest

class FileMapper(object):
    ''' A file mapper is a tree of rules used to enumerate files.
        TODO : Eventuellement utiliser les PurePath, de python 3.4, qui simplifieraient
        quelque trucs, nottament dans les globs.
    '''
    def __init__(self, mapper, format_args = None):
        super(FileMapper, self).__init__()
        self._mapper = mapper
        self._next = []
        self._format_args = format_args if format_args is not None else {}

    def __call__(self, src = None, dest = None):
        results = self._mapper(src, dest)
        for result in sorted(results, key = lambda t: t[1] or t[0] or ""):
            for next_mapper in self._next:
                for next_result in next_mapper(*result):
                    yield next_result
            # Only test the left element because some filemappers only worry about source
            if not self._next and result[0] is not None:
                yield result

    def glob(self, *patterns):
        ''' Globs given patterns, feedding the resulting files '''
        def _glob_mapper(src, dest):
            src = nimp.utilities.system.sanitize_path(src)
            dest = nimp.utilities.system.sanitize_path(dest)
            if src is None or src == '.':
                source_path_len = 0
            else:
                source_path_len = len(nimp.utilities.system.split_path(src))

            for pattern in patterns:
                found = False
                pattern = self._format(pattern)
                if src is None:
                    glob_path = pattern
                else:
                    glob_path = os.path.join(src, pattern)

                for glob_source in glob2.glob(glob_path):
                    found = True
                    glob_source = str(glob_source)
                    # This is merely equivalent to os.path.relpath(src, self._source_path)
                    # except it will handle globs pattern in the base path.
                    glob_source = os.path.normpath(glob_source)
                    if dest is not None:
                        new_dest = nimp.utilities.system.split_path(glob_source)[source_path_len:]
                        new_dest = '/'.join(new_dest)
                        new_dest = os.path.join(dest, new_dest)
                        new_dest = os.path.normpath(new_dest)
                    else:
                        new_dest = None

                    yield (glob_source, new_dest)
                if not found:
                    logging.error("No match for “%s” in “%s” (aka. “%s”)", pattern, src, glob_path)
                    #raise Exception("No match for “%s” in “%s” (aka. “%s”)" % (pattern, src, glob_path))
        return self.append(_glob_mapper)

    def xglob(self, src = '.', dst = '.', pattern = '**'):
        ''' More user-friendly glob '''
        return self.src(src).to(dst).glob(pattern)

    def append(self, mapper, format_args = None):
        ''' Appends a filter / generator function to the end of this mapper '''
        next_mapper = FileMapper(mapper, format_args or self._format_args)
        self._next.append(next_mapper)
        return next_mapper

    def load_set(self, set_name):
        ''' Loads a file mapper from a configuration file '''
        file_name = self._format(set_name)
        if not os.path.exists(file_name) or not os.path.isfile(file_name):
            # Always hardcode this directory to avoid bloating .nimp.conf.
            file_name = os.path.join(self.root_dir, ".nimp/filesets", set_name + ".txt")
            file_name = self._format(file_name)
        locals_vars = {}
        try:
            conf = open(file_name, "rb").read()
        except IOError as exception:
            logging.error("Error loading fileset: unable to open file: %s", exception)
            return None

        try:
            #pylint: disable=exec-used
            exec(compile(conf, file_name, 'exec'), None, locals_vars)
            if "map" not in locals_vars:
                logging.error("Configuration file %s has no function called 'map'.", file_name)
                return None
        #pylint: disable=broad-except
        except Exception as ex:
            logging.error("Error loading fileset: unable to load file %s : %s", file_name, str(ex))
            return None

        locals_vars['map'](self)

        return self._get_leaves()


    def get_leaves(self):
        ''' Return all terminal leaves of the tree. '''
        for mapper in self._next:
            for leaf in mapper.get_leaves():
                yield leaf
        if not self._next:
            yield self

    def override(self, **fmt):
        ''' Inserts a node adding or overriding given format arguments. '''
        format_args = self._format_args.copy()
        format_args.update(fmt)
        return self.append(_identity_mapper, format_args = format_args)

    def exclude(self, *patterns):
        ''' Exclude file patterns from the set '''
        return self._exclude(False, *patterns)

    def exclude_ignore_case(self, *patterns):
        ''' Exclude file patterns from the set ignoring case '''
        return self._exclude(True, *patterns)

    def _exclude(self, ignore_case, *patterns):
        def _exclude_mapper(src, dest):
            for pattern in patterns:
                pattern = self._format(pattern)
                real_src = src.lower() if ignore_case else src
                real_pattern = pattern.lower() if ignore_case else pattern
                if fnmatch.fnmatch(real_src, real_pattern):
                    logging.debug("Excluding file %s", src)
                    raise StopIteration()
            yield (src, dest)
        return self.append(_exclude_mapper)

    def files(self):
        ''' Discards directories from processed paths '''
        def _files_mapper(src, dest):
            if os.path.isfile(src):
                yield (src, dest)
        return self.append(_files_mapper)

    def src(self, from_src):
        ''' Prepends 'src' to path given to subsequent calls.
        '''
        from_src = self._format(from_src)
        def _src_mapper(src, dest):
            if src is None:
                src = from_src
            else:
                src = os.path.join(self._format(src), from_src)
            src = os.path.normpath(nimp.utilities.system.sanitize_path(src))
            yield (src, dest)
        return self.append(_src_mapper)

    def once(self):
        ''' Stores processed files and don't process them if they already have been.
        '''
        processed_files = set()
        def _once_mapper(src, dest):
            if src is None:
                raise Exception("once() called on empty fileset")
            if src not in processed_files:
                processed_files.add(src)
                yield (src, dest)

        return self.append(_once_mapper)

    def newer(self):
        ''' Ignore files when source is newer than destination.
        '''
        def _newer_mapper(src, dest):
            if src is None or dest is None:
                raise Exception("newer() called on empty fileset")
            if not os.path.exists(dest):
                yield (src, dest)
            elif os.path.getmtime(src) > os.path.getmtime(dest):
                yield (src, dest)

        return self.append(_newer_mapper)

    def recursive(self):
        ''' Recurvively list all children of processed source if it is a
            directory.
        '''
        def _recursive_mapper(src, dest):
            if src is None:
                raise Exception("recursive() called on empty fileset")
            yield (src, dest)
            if os.path.isdir(src):
                for file in os.listdir(src):
                    child_source = os.path.normpath(os.path.join(src, file))
                    if dest is not None:
                        child_dest = os.path.normpath(os.path.join(dest, file))
                    else:
                        child_dest = os.path.normpath(file)
                    for child_source, child_destination in _recursive_mapper(child_source, child_dest):
                        yield (child_source, child_destination)
        return self.append(_recursive_mapper)

    def replace(self, pattern, repl, flags = 0):
        ''' Performs a re.sub on destination
        '''
        pattern = self._format(pattern)
        repl = self._format(repl)
        def _replace_mapper(src, dest):
            if dest is None:
                raise Exception("replace() called with dest = None")
            dest = re.sub(pattern, repl, dest, flags = flags)
            yield (src, dest)
        return self.append(_replace_mapper)

    #pylint: disable=invalid-name
    def to(self, to_destination):
        ''' Inserts a nodes prepending given 'to_destination' to each destination
            path processed.
        '''
        to_destination = self._format(to_destination)
        def _to_mapper(src, dest):
            if dest is None:
                dest = to_destination
            else:
                dest = os.path.join(dest, to_destination)
            dest = nimp.utilities.system.sanitize_path(dest)
            yield (src, dest)
        return self.append(_to_mapper)

    def upper(self):
        ''' Yields all destination files uppercase
        '''
        def _upper_mapper(src, dest):
            if dest is None:
                raise Exception("upper() called with dest = None")
            yield (src, dest.upper())
        return self.append(_upper_mapper)

    def _format(self, fmt):
        ''' Formats given string using format arguments defined on all the
            nodes of the list.
        '''
        result = fmt.format(**self._format_args)
        result = time.strftime(result)
        return result

    def __getattr__(self, name):
        ''' Usefull to simply retrieve format arguments, in config files for example.
        '''
        try:
            return self._format_args[name]
        except KeyError:
            raise AttributeError(name)

