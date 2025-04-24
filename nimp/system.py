# -*- coding: utf-8 -*-
# Copyright (c) 2014-2019 Dontnod Entertainment

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

'''System utilities (paths, processes)'''

from __future__ import annotations

import fnmatch
import importlib
import json
import logging
import os
import re
import shutil
import stat
import time
from typing import TYPE_CHECKING

import glob2

import nimp.environment
import nimp.sys.platform
import nimp.sys.process
from nimp.utils.python import iter_plugins_entry_points

if TYPE_CHECKING:
    from typing import overload


def try_import(module_name):
    '''Tries to import a module, return none if unavailable'''
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        pass  # Ignore this error
    except ImportError as ex:
        if ex.name == module_name:
            logging.debug('No module %s found', module_name)
        else:
            logging.warning('%s', ex)
    return None


def try_execute(action, exception_types, attempt_maximum=5, retry_delay=10):
    '''Attempts to execute an action, and retries when catching one of the specified exceptions'''
    attempt = 1
    while attempt <= attempt_maximum:
        try:
            return action()
        except exception_types as exception:
            logging.warning('%s (Attempt %s of %s)', exception, attempt, attempt_maximum)
            if attempt >= attempt_maximum:
                raise exception
            time.sleep(retry_delay)
            attempt += 1


def try_remove(file_path, dry_run):
    if os.path.exists(file_path):
        logging.info("Removing %s", file_path)
        if not dry_run:
            try:
                if os.path.isdir(file_path):
                    safe_rmtree(file_path)
                else:
                    os.remove(file_path)
            except OSError as exception:
                logging.warning("Failed to remove %s: %s", file_path, exception)


def split_path(path):
    '''Returns an array of path elements'''
    splitted_path = []
    while True:
        (path, folder) = os.path.split(path)

        if folder != "":
            splitted_path.insert(0, folder)
        else:
            if path != "":
                splitted_path.insert(0, path)
            break

    return splitted_path


def path_to_array(path):
    '''Splits a path to an array'''
    directory, file = os.path.split(path)
    return path_to_array(directory) + [file] if directory else [file]


def standardize_path(path):
    '''Transform a path to appear the same across operating systems'''
    return os.path.normpath(path).replace('\\', '/') if path else path


if TYPE_CHECKING:

    @overload
    def sanitize_path(path: None) -> None: ...

    @overload
    def sanitize_path(path: str) -> str: ...


def sanitize_path(path: str | None) -> str | None:
    '''Performs slash replacement to work on both msys and windows'''
    if path is None:
        return None

    if nimp.sys.platform.is_windows() and not nimp.sys.platform.is_msys():
        if path[0:1] == '/' and path[1:2].isalpha() and path[2:3] == '/':
            return '%s:\\%s' % (path[1], path[3:].replace('/', '\\'))

    if os.sep == '\\':
        return path.replace('/', '\\')

    # elif os.sep == '/':
    return path.replace('\\', '/')


def safe_rmtree(path):
    def remove_readonly(func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(path, onerror=remove_readonly)


def safe_makedirs(path):
    '''This function is necessary because Python’s makedirs cannot create a
    directory such as d:\\data\\foo/bar because it’ll split it as "d:\\data"
    and "foo/bar" then try to create a directory named "foo/bar"'''
    path = sanitize_path(path)

    try:
        os.makedirs(path)
    except FileExistsError:
        # Maybe someone else created the directory for us; if so, ignore error
        if os.path.exists(path):
            return
        raise


def robocopy(src, dest, ignore_older=False, preserve_metadata=True):
    ''' 'Robust' copy.'''

    # Retry up to 5 times after I/O errors
    max_retries = 10

    src = sanitize_path(src)
    dest = sanitize_path(dest)

    if (
        ignore_older
        and os.path.isfile(src)
        and os.path.isfile(dest)
        and os.stat(src).st_mtime - os.stat(dest).st_mtime < 1
    ):
        logging.info('Skipping "%s", not newer than "%s"', src, dest)
        return True

    logging.debug('Copying "%s" to "%s"', src, dest)

    if os.path.isdir(src):
        safe_makedirs(dest)
    elif os.path.isfile(src):
        dest_dir = os.path.dirname(dest)
        safe_makedirs(dest_dir)
        while True:
            try:
                if os.path.exists(dest):
                    os.chmod(dest, stat.S_IRWXU)
                copy_function = shutil.copy2 if preserve_metadata else shutil.copy
                copy_function(src, dest)
                os.chmod(dest, stat.S_IRWXU)
                break
            except IOError as ex:
                logging.warning('I/O error %s : %s', ex.errno, ex.strerror)
                max_retries -= 1
                if max_retries <= 0:
                    logging.error('Error copying %s to %s (%s : %s)', src, dest, ex.errno, ex.strerror)
                    return False
                logging.warning('Retrying after 10 seconds (%s retries left)', max_retries)
                time.sleep(10)
            except Exception as ex:  # pylint: disable=broad-except
                logging.error('Copy error: %s', ex)
                return False
    else:
        logging.error('Error: not such file or directory "%s"', src)
        return False

    return True


def safe_delete(path):
    ''' 'Robust' delete.'''

    path = sanitize_path(path)

    if os.path.isfile(path):
        try:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            os.remove(path)
        except OSError:
            pass


def all_map(mapper, fileset):
    '''Passes all the files in the given fileset and checks it returns true
    for every file'''
    for src, dest in fileset:
        if src is None:
            pass
        if not mapper(src, dest):
            return False
    return True


def find_dir_containing_file(filename):
    '''Recursively search parent directories for a file'''
    search_dir = '.'
    while os.path.abspath(os.sep) != os.path.abspath(search_dir):
        if os.path.exists(os.path.join(search_dir, filename)):
            break
        search_dir = os.path.join('..', search_dir)

    if not os.path.isfile(os.path.join(search_dir, filename)):
        return None

    return search_dir


def map_files(env):
    '''Returns a file mapper using environment parameters'''
    ctx = [None]

    def _default_mapper(_, dest):
        yield (env.root_dir if ctx[0].root_based else None, dest)

    ret = FileMapper(_default_mapper, format_args=vars(env))
    ctx[0] = ret
    return ret


class FileMapper:
    '''A file mapper is a tree of rules used to enumerate files.
    TODO : Eventuellement utiliser les PurePath, de python 3.4, qui simplifieraient
    quelque trucs, nottament dans les globs.
    '''

    def __init__(self, mapper, format_args=None):
        super(FileMapper, self).__init__()
        self._mapper = mapper
        self._next = []
        self._format_args = format_args if format_args is not None else {}
        # True for legacy mode: filesets are relative to {root_dir}, not current directory
        # Newer filesets should explicitly use {root_dir} or {unreal_dir} etc.
        self.root_based = True

    def __call__(self, src=None, dest=None):
        results = self._mapper(src, dest) if self._mapper else [(src, dest)]
        for result in sorted(results, key=lambda t: t[1] or t[0] or ""):
            for next_mapper in self._next:
                for next_result in next_mapper(*result):
                    yield next_result
            # Only test the left element because some filemappers only worry about source
            if not self._next and result[0] is not None:
                yield result

    def glob(self, *patterns):
        '''Globs given patterns, feedding the resulting files'''

        def _glob_mapper(src, dest):
            src = sanitize_path(src)
            dest = sanitize_path(dest)
            if src is None or src == '.':
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

                for glob_source in glob2.glob(glob_path, include_hidden=True):
                    found = True
                    glob_source = str(glob_source)
                    # This is merely equivalent to os.path.relpath(src, self._source_path)
                    # except it will handle globs pattern in the base path.
                    glob_source = os.path.normpath(glob_source)
                    if dest is not None:
                        new_dest = split_path(glob_source)[source_path_len:]
                        new_dest = '/'.join(new_dest)
                        new_dest = os.path.join(dest, new_dest)
                        new_dest = os.path.normpath(new_dest)
                    else:
                        new_dest = None

                    yield (glob_source, new_dest)
                if not found:
                    logging.info('No match for "%s" in "%s" (aka. "%s")', pattern, src, glob_path)

        return self.append(_glob_mapper)

    def xglob(self, src='.', dest='.', pattern='**'):
        '''More user-friendly glob'''
        return self.src(src).to(dest).glob(pattern)

    def append(self, mapper, format_args=None):
        '''Appends a filter / generator function to the end of this mapper'''
        next_mapper = FileMapper(mapper, format_args or self._format_args)
        self._next.append(next_mapper)
        return next_mapper

    def load_set(self, set_name):
        '''Loads a file mapper from a configuration file'''
        set_module_name = self._format(set_name)
        set_module = None
        try:
            set_module = importlib.import_module('filesets.' + set_module_name)
        except ModuleNotFoundError:
            for entry in iter_plugins_entry_points():
                try:
                    set_module = importlib.import_module(entry.module + '.filesets.' + set_module_name)
                    break
                except ModuleNotFoundError:
                    pass
        if set_module is None:
            raise ModuleNotFoundError(f"No module named 'filesets.{set_module_name}'")

        set_module.map(self)
        return self.get_leaves()

    def get_leaves(self):
        '''Return all terminal leaves of the tree.'''
        for mapper in self._next:
            for leaf in mapper.get_leaves():
                yield leaf
        if not self._next:
            yield self

    def override(self, **fmt):
        '''Inserts a node adding or overriding given format arguments.'''

        def _identity_mapper(src, dest):
            yield src, dest

        format_args = self._format_args.copy()
        # Hackish : We construct a new Environment to load load_arguments so
        # values computed from others parameters are correctly set
        # (like unreal_config, for example)
        new_env = nimp.environment.Environment()
        format_args.update(fmt)
        for key, value in format_args.items():
            setattr(new_env, key, value)
        new_env.load_arguments()
        format_args = vars(new_env)
        return self.append(_identity_mapper, format_args=format_args)

    def exclude(self, *patterns):
        '''Exclude file patterns from the set'''
        return self._exclude(False, *patterns)

    def exclude_ignore_case(self, *patterns):
        '''Exclude file patterns from the set ignoring case'''
        return self._exclude(True, *patterns)

    def _exclude(self, ignore_case, *patterns):
        def _exclude_mapper(src, dest):
            for pattern in patterns:
                pattern = self._format(pattern)
                real_src = src.lower() if ignore_case else src
                real_pattern = pattern.lower() if ignore_case else pattern
                if fnmatch.fnmatch(real_src, real_pattern):
                    logging.debug("Excluding file %s", src)
                    return
            yield (src, dest)

        return self.append(_exclude_mapper)

    def files(self):
        '''Discards directories from processed paths'''

        def _files_mapper(src, dest):
            if os.path.isfile(src):
                yield (src, dest)

        return self.append(_files_mapper)

    def src(self, from_src):
        '''Prepends 'src' to path given to subsequent calls.'''
        from_src = self._format(from_src)

        def _src_mapper(src, dest):
            if src is None:
                src = from_src
            else:
                src = os.path.join(self._format(src), from_src)
            src = os.path.normpath(sanitize_path(src))
            yield (src, dest)

        return self.append(_src_mapper)

    def once(self):
        '''Stores processed files and don't process them if they already have been.'''
        processed_files = set()

        def _once_mapper(src, dest):
            if src is None:
                raise Exception("once() called on empty fileset")
            if src not in processed_files:
                processed_files.add(src)
                yield (src, dest)

        return self.append(_once_mapper)

    def newer(self):
        '''Ignore files when source is newer than destination.'''

        def _newer_mapper(src, dest):
            if src is None or dest is None:
                raise Exception("newer() called on empty fileset")
            if not os.path.exists(dest):
                yield (src, dest)
            elif os.path.getmtime(src) > os.path.getmtime(dest):
                yield (src, dest)

        return self.append(_newer_mapper)

    def recursive(self):
        '''Recurvively list all children of processed source if it is a
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

    def replace(self, pattern, repl, flags=0):
        '''Performs a re.sub on destination'''
        pattern = self._format(pattern)
        repl = self._format(repl)

        def _replace_mapper(src, dest):
            if dest is None:
                raise Exception("replace() called with dest = None")
            dest = re.sub(pattern, repl, dest, flags=flags)
            yield (src, dest)

        return self.append(_replace_mapper)

    # pylint: disable=invalid-name
    def to(self, to_destination):
        '''Inserts a nodes prepending given 'to_destination' to each destination
        path processed.
        '''
        to_destination = self._format(to_destination)

        def _to_mapper(src, dest):
            if dest is None:
                dest = to_destination
            else:
                dest = os.path.join(dest, to_destination)
            dest = sanitize_path(dest)
            yield (src, dest)

        return self.append(_to_mapper)

    def upper(self):
        '''Yields all destination files uppercase'''

        def _upper_mapper(src, dest):
            if dest is None:
                raise Exception("upper() called with dest = None")
            yield (src, dest.upper())

        return self.append(_upper_mapper)

    def _format(self, fmt):
        '''Formats given string using format arguments defined on all the
        nodes of the list.
        '''
        result = fmt.format(**self._format_args)
        result = time.strftime(result)
        return result

    def __getattr__(self, name):
        '''Usefull to simply retrieve format arguments, in config files for example.'''
        try:
            return self._format_args[name]
        except KeyError:
            raise AttributeError(name)

    def to_list(self, mapper_source=None, mapper_destination=None):
        '''Helper to execute a file mapper and organize the result'''
        default_result = [(standardize_path(mapper_source), standardize_path(mapper_destination))]
        all_files = self(mapper_source, mapper_destination)
        all_files = list(sorted(set(((standardize_path(src), standardize_path(dest)) for src, dest in all_files))))
        return all_files if all_files != default_result else []


def load_status(env):
    '''Loads the workspace status'''
    status_file_path = os.path.join(env.root_dir, '.nimp', 'status.json')
    if not os.path.exists(status_file_path):
        return {'binaries': {}, 'symbols': {}, 'staged': {}, 'package': {}}
    with open(status_file_path) as status_file:
        return json.load(status_file)


def save_status(env, status):
    '''Saves the workspace status'''
    status_file_path = os.path.join(env.root_dir, '.nimp', 'status.json')
    with open(status_file_path, 'w') as status_file:
        return json.dump(status, status_file, indent=4)
