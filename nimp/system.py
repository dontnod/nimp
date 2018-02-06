# -*- coding: utf-8 -*-
# Copyright © 2014—2017 Dontnod Entertainment

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
''' System utilities (paths, processes) '''

import datetime
import fnmatch
import glob
import logging
import os
import os.path
import re
import shutil
import stat
import time
import importlib

import glob2
import requests

import nimp.environment
import nimp.sys.platform
import nimp.sys.process

def try_import(module_name):
    ''' Tries to import a module, return none if unavailable '''
    try:
        return importlib.import_module(module_name)
    except ImportError as ex:
        if ex.name == module_name:
            logging.debug('No module %s found', module_name)
        else:
            logging.warning('%s', ex)
        return None

def split_path(path):
    ''' Returns an array of path elements '''
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
    ''' Splits a path to an array '''
    directory, file = os.path.split(path)
    return path_to_array(directory) + [file] if directory  else [file]

def sanitize_path(path):
    ''' Perfmorms slash replacement to work on both msys and windows '''
    if path is None:
        return None

    if nimp.sys.platform.is_windows() and not nimp.sys.platform.is_msys():
        if path[0:1] == '/' and path[1:2].isalpha() and path[2:3] == '/':
            return '%s:\\%s' % (path[1], path[3:].replace('/', '\\'))

    if os.sep is '\\':
        return path.replace('/', '\\')

    # elif os.sep is '/':
    return path.replace('\\', '/')

def safe_makedirs(path):
    ''' This function is necessary because Python’s makedirs cannot create a
        directory such as d:\\data\\foo/bar because it’ll split it as "d:\\data"
        and "foo/bar" then try to create a directory named "foo/bar" '''
    path = sanitize_path(path)

    try:
        os.makedirs(path)
    except FileExistsError:
        # Maybe someone else created the directory for us; if so, ignore error
        if os.path.exists(path):
            return
        raise


def robocopy(src, dest, ignore_older=False):
    ''' 'Robust' copy. '''

    # Retry up to 5 times after I/O errors
    max_retries = 10

    src = sanitize_path(src)
    dest = sanitize_path(dest)

    if ignore_older and os.path.isfile(src) and os.path.isfile(dest) \
       and os.stat(src).st_mtime - os.stat(dest).st_mtime < 1:
        logging.info('Skipping “%s”, not newer than “%s”', src, dest)
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
                shutil.copy2(src, dest)
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
            except Exception as ex: #pylint: disable=broad-except
                logging.error('Copy error: %s', ex)
                return False
    else:
        logging.error('Error: not such file or directory “%s”', src)
        return False

    return True

def safe_delete(path):
    ''' 'Robust' delete. '''

    path = sanitize_path(path)

    if os.path.isfile(path):
        try:
            os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            os.remove(path)
        except OSError:
            pass


def all_map(mapper, fileset):
    ''' Passes all the files in the given fileset and checks it returns true
        for every file '''
    for src, dest in fileset:
        if src is None:
            pass
        if not mapper(src, dest):
            return False
    return True

def load_arguments(env):
    '''Sets default platform '''
    if not hasattr(env, 'platform') or env.platform is None:
        if nimp.sys.platform.is_windows():
            env.platform = 'win64'
        elif nimp.sys.platform.is_osx():
            env.platform = 'mac'
        else:
            env.platform = 'linux'

    return True

def map_files(env):
    ''' Returns a file mapper using environment parameters '''
    def _default_mapper(_, dest):
        yield (env.root_dir, dest)

    return FileMapper(_default_mapper, format_args = vars(env))

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

                for glob_source in glob2.glob(glob_path):
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
                    logging.info("No match for “%s” in “%s” (aka. “%s”)", pattern, src, glob_path)
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
        set_module_name = self._format(set_name)
        set_path = os.path.join(self.root_dir, ".nimp/filesets", set_module_name + ".py")

        if os.path.exists(set_path):
            set_module = importlib.import_module('filesets.' + set_module_name)
            set_module.map(self)
            return self.get_leaves()

        # Fallback deprecated behavior for .txt file
        return self._load_set_from_txt(set_name)

    # Deprecated
    def _load_set_from_txt(self, set_name):
        ''' Loads a file mapper from a configuration file '''
        file_name = self._format(set_name)
        if not os.path.exists(file_name) or not os.path.isfile(file_name):
            # Always hardcode this directory to avoid bloating .nimp.conf.
            file_name = os.path.join(self.root_dir, ".nimp/filesets", set_name + ".txt")
            file_name = self._format(file_name)
        locals_vars = {}
        try:
            conf = open(file_name, "rb").read()
        except IOError as ex:
            logging.error("Error loading fileset: unable to open file: %s", ex)
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

        return self.get_leaves()

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
        # Hackish : We construct a new Environment to load load_arguments so
        # values computed from others parameters are correctly set
        # (like ue4_config, for example)
        new_env = nimp.environment.Environment()
        format_args.update(fmt)
        for key, value in format_args.items():
            setattr(new_env, key, value)
        new_env.load_arguments()
        format_args = vars(new_env)
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
            src = os.path.normpath(sanitize_path(src))
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
            dest = sanitize_path(dest)
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

def list_all_revisions(env, archive_location_format, **override_args):
    ''' Lists all revisions based on pattern '''

    revisions_info = []

    http_match = re.match('^http(s?)://.*$', archive_location_format)
    is_http = http_match is not None

    format_args = {'revision' : '*',
                   'platform' : '*',
                   'dlc' : '*',
                   'configuration' : '*'}

    format_args.update(vars(env).copy())
    format_args.update(override_args)

    if format_args['revision'] is None:
        format_args['revision'] = '*'
    if format_args['platform'] is None:
        format_args['platform'] = '*'
    if format_args['dlc'] is None:
        format_args['dlc'] = '*'
    if format_args['configuration'] is None:
        format_args['configuration'] = '*'

    # Preparing to search (either on a http directory listing or directly with a glob)
    logging.debug('Looking for latest revision in %s…', archive_location_format)
    if is_http:
        listing_url, _, archive_pattern = archive_location_format.format(**format_args).rpartition("/")
        archive_regex = fnmatch.translate(archive_pattern)
    else:
        archive_location_format = sanitize_path(archive_location_format)
        archive_location_format = archive_location_format.replace('\\', '/')
        archive_glob = archive_location_format.format(**format_args)

    # Preparing for capture after search
    format_args.update({'revision'      : r'(?P<revision>\d+)',
                        'platform'      : r'(?P<platform>\w+)',
                        'dlc'           : r'(?P<dlc>\w+)',
                        'configuration' : r'(?P<configuration>\w+)'})

    if is_http:
        get_request = requests.get(listing_url)
        # TODO: test get_request.ok and/or get_request.status_code...
        listing_content = get_request.text
        _, _, archive_capture_regex = archive_location_format.format(**format_args).rpartition("/")
        for line in listing_content.splitlines():
            extract_revision_info_from_html(revisions_info, listing_url, line, archive_regex, archive_capture_regex)
    else:
        archive_capture_regex = archive_location_format.format(**format_args)
        for archive_path in glob.glob(archive_glob):
            archive_path = archive_path.replace('\\', '/')
            extract_revision_info_from_path(revisions_info, archive_path, archive_capture_regex)

    return sorted(revisions_info, key=lambda ri: ri['revision'], reverse = True)

def extract_revision_info_from_html(revisions_info, listing_url, line, archive_regex, archive_capture_regex):
    ''' Extracts revision info by parsing a line from a html directory listing
        (looking at anchors) (if it's a match) '''
    anchor_extractor = '^.*<a href="(?P<anchor_target>.+)">.*$'
    anchor_match = re.match(anchor_extractor, line)

    if anchor_match is not None:
        anchor_target = anchor_match.groupdict()['anchor_target']
        revision_match = re.match(archive_regex, anchor_target)
        revision_capture_match = re.match(archive_capture_regex, anchor_target)

        if revision_match is not None and revision_capture_match is not None:
            revision_info = revision_capture_match.groupdict()
            revision_info['is_http'] = True
            revision_info['location'] = '/'.join([listing_url, anchor_target])
            revisions_info += [revision_info]

def extract_revision_info_from_path(revisions_info, archive_path, archive_capture_regex):
    ''' Extracts revision info from a filename (if it's a match) '''
    revision_match = re.match(archive_capture_regex, archive_path)

    if revision_match is not None:
        revision_info = revision_match.groupdict()
        revision_info['is_http'] = False
        revision_info['location'] = archive_path
        revision_info['creation_date'] = datetime.date.fromtimestamp(os.path.getctime(archive_path))
        revisions_info += [revision_info]

def get_latest_available_revision(env, archive_location_format, max_revision, min_revision, **override_args):
    ''' Returns the latest available revision based on pattern '''
    revisions_info = list_all_revisions(env, archive_location_format, **override_args)
    for revision_info in revisions_info:
        revision = revision_info['revision']
        if ((max_revision is None or int(revision) <= int(max_revision)) and
                (min_revision is None or int(revision) >= int(min_revision))):
            logging.debug('Found revision %s', revision)
            return revision_info

    revisions = [revision_info['revision'] for revision_info in revisions_info]
    candidates_desc = (' Candidates were: %s' % ' '.join(revisions)) if revisions_info else ''
    if env.revision is not None:
        revision_desc = ' equal to %s' % env.revision
    elif max_revision is not None and min_revision is not None:
        revision_desc = ' <= %s and >= %s' % (max_revision, min_revision)
    elif max_revision is not None:
        revision_desc = ' <= %s' % max_revision
    elif min_revision is not None:
        revision_desc = ' >= %s' % min_revision
    else:
        revision_desc = ''
    raise Exception('No revision%s found.%s' % (revision_desc, candidates_desc))

def load_or_save_last_deployed_revision(env, mode):
    ''' Loads or saves the last deployed revision '''
    last_deployed_revision = env.revision if mode == 'save' else None
    memo_path = nimp.system.sanitize_path(os.path.abspath(os.path.join(env.root_dir, '.nimp', 'utils', 'last_deployed_revision.txt')))
    if mode == 'save':
        safe_makedirs(os.path.dirname(memo_path))
        with open(memo_path, 'w') as memo_file:
            memo_file.write(last_deployed_revision)
    elif mode == 'load':
        if os.path.isfile(memo_path):
            with open(memo_path, 'r') as memo_file:
                last_deployed_revision = memo_file.read()
    return last_deployed_revision

def save_last_deployed_revision(env):
    ''' Saves the last deployed revision '''
    load_or_save_last_deployed_revision(env, 'save')

def load_last_deployed_revision(env):
    ''' Loads the last deployed revision '''
    return load_or_save_last_deployed_revision(env, 'load')

def _identity_mapper(src, dest):
    yield src, dest
