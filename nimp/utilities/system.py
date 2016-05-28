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
''' System utilities (paths, processes) '''

import datetime
import fnmatch
import glob
import logging
import os
import os.path
import platform
import re
import stat
import subprocess
import sys
import threading
import time

import glob2

import nimp.utilities.windows

def is_windows():
    ''' Return True if the runtime platform is Windows, including MSYS '''
    return is_msys() or platform.system() == 'Windows'

# Return True if the runtime platform is MSYS
def is_msys():
    ''' Returns True if the platform is msys. '''
    return platform.system()[0:7] == 'MSYS_NT'

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

    if is_windows() and not is_msys():
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

def capture_process_output(directory, command, stdin = None, encoding = 'utf-8'):
    ''' Returns a 3-uple containing return code, stdout and stderr of the given
        command '''
    command = _sanitize_command(command)
    logging.debug("Running “%s” in “%s”", " ".join(command), os.path.abspath(directory))
    process = subprocess.Popen(command,
                               cwd     = directory,
                               stdout  = subprocess.PIPE,
                               stderr  = subprocess.PIPE,
                               stdin   = subprocess.PIPE,
                               bufsize = 1)
    output, error = process.communicate(stdin.encode(encoding) if stdin else None)

    return process.wait(), output.decode(encoding), error.decode(encoding)

def call_process(directory, command, heartbeat = 0):
    ''' Calls a process redirecting its output to nimp's output '''
    command = _sanitize_command(command)
    logging.debug("Running “%s” in “%s”", " ".join(command), os.path.abspath(directory))

    if is_windows():
        nimp.utilities.windows.disable_win32_dialogs()
        debug_pipe = nimp.utilities.windows.OutputDebugStringLogger()

    # The bufsize = 1 is important; if we don’t bufferise the
    # output, we’re going to make the callee lag a lot.
    process = subprocess.Popen(command,
                               cwd     = directory,
                               stdout  = subprocess.PIPE,
                               stderr  = subprocess.PIPE,
                               stdin   = None,
                               bufsize = 1)
    if is_windows():
        debug_pipe.attach(process.pid)
        debug_pipe.start()

    def _heartbeat_worker(heartbeat):
        last_time = time.monotonic()
        while process:
            if heartbeat > 0 and time.monotonic() > last_time + heartbeat:
                logging.info("Keepalive for %s", command[0])
                last_time += heartbeat
            time.sleep(0.050)

    def _output_worker(in_pipe, out_pipe):
        # FIXME: it would be better to use while process.poll() == None
        # here, but thread safety issues in Python < 3.4 prevent it.
        while process:
            try:
                for line in iter(in_pipe.readline, ''):
                    try:
                        line = line.decode("utf-8")
                    except UnicodeError:
                        line = line.decode("cp850")

                    if line == '':
                        break

                    out_pipe.write(line)

                # Sleep for 10 milliseconds if there was no data,
                # or we’ll hog the CPU.
                time.sleep(0.010)

            except ValueError:
                return

    log_thread_args = [ (process.stdout, sys.stdout),
                        (process.stderr, sys.stderr) ]
    if is_windows():
        log_thread_args += [ (debug_pipe.output, sys.stdout) ]

    worker_threads = [ threading.Thread(target = _output_worker, args = args) for args in log_thread_args ]
    # Send keepalive to stderr if requested
    if heartbeat > 0:
        worker_threads += [ threading.Thread(target = _heartbeat_worker, args = (heartbeat, )) ]

    for thread in worker_threads:
        thread.start()

    try:
        process_return = process.wait()
    finally:
        process = None
        if is_windows():
            debug_pipe.stop()
        for thread in worker_threads:
            thread.join()

    if process_return == 0:
        log = logging.debug
    else:
        log = logging.error
    log("Program “%s” finished with exit code %s", command[0], process_return)

    return process_return

def robocopy(src, dest):
    ''' 'Robust' copy. '''

    # Retry up to 5 times after I/O errors
    max_retries = 10

    src = nimp.utilities.system.sanitize_path(src)
    dest = nimp.utilities.system.sanitize_path(dest)

    logging.debug('Copying “%s” to “%s”', src, dest)

    if os.path.isdir(src):
        nimp.utilities.system.safe_makedirs(dest)
    elif os.path.isfile(src):
        dest_dir = os.path.dirname(dest)
        nimp.utilities.system.safe_makedirs(dest_dir)
        while True:
            try:
                if os.path.exists(dest):
                    os.chmod(dest, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                shutil.copy2(src, dest)
                break
            except IOError as ex:
                logging.error('I/O error %s : %s', ex.errno, ex.strerror)
                max_retries -= 1
                if max_retries <= 0:
                    return False
                logging.error('Retrying after 10 seconds (%s retries left)', max_retries)
                time.sleep(10)

            except Exception as ex: #pylint: disable=broad-except
                logging.error('Copy error: %s', ex)
                return False
    else:
        logging.error('Error: not such file or directory “%s”', src)
        return False

    return True

def force_delete(path):
    ''' 'Robust' delete. '''

    path = nimp.utilities.system.sanitize_path(path)

    if os.path.exists(path):
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.remove(path)


def _sanitize_command(command):
    new_command = []
    for it in command:
        # If we’re running under MSYS, leading slashes in command line arguments
        # will be treated as a path, so we need to escape them, except if the given
        # argument is indeed a file.
        if it[0:1] == '/':
            if is_msys():
                # If the argument starts with /, we may wish to rewrite it
                if it[1:2].isalpha() and it[2:3] == '/':
                    # Stuff like /c/... looks like a path with a drive letter, keep it that way
                    # but /c is most probably a flag, so that one needs to be escaped
                    pass
                elif len(it) > 5 and (os.path.isfile(it) or os.path.isdir(it)):
                    pass
                else:
                    it = '/' + it
        new_command.append(it)
    return new_command

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

def list_all_revisions(env, version_directory_format, **override_args):
    ''' Lists all revisions based on directory pattern '''
    version_directory_format = nimp.utilities.system.sanitize_path(version_directory_format)
    revisions = []
    format_args = { 'revision' : '*',
                    'platform' : '*',
                    'dlc' : '*',
                    'configuration' : '*' }

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

    version_directory_format = version_directory_format.replace('\\', '/')
    version_directories_glob = version_directory_format.format(**format_args)

    format_args.update({'revision'      : r'(?P<revision>\d+)',
                        'platform'      : r'(?P<platform>\w+)',
                        'dlc'           : r'(?P<dlc>\w+)',
                        'configuration' : r'(?P<configuration>\w+)'})

    logging.debug('Looking for latest version in %s…', version_directory_format)

    for version_file in glob.glob(version_directories_glob):
        version_file = version_file.replace('\\', '/')
        version_regex = version_directory_format.format(**format_args)

        rev_match = re.match(version_regex, version_file)

        if rev_match is not None:
            rev_infos = rev_match.groupdict()
            rev_infos['path'] = version_file
            rev_infos['creation_date'] = datetime.date.fromtimestamp(os.path.getctime(version_file))

            if 'platform' not in rev_infos:
                rev_infos['platform'] = "*"
            if 'dlc' not in rev_infos:
                rev_infos['dlc'] = "*"
            if 'configuration' not in rev_infos:
                rev_infos['configuration'] = "*"

            rev_infos['rev_type'] = '{dlc}_{platform}_{configuration}'.format(**rev_infos)
            revisions += [rev_infos]

    return sorted(revisions, key=lambda rev_infos: rev_infos['revision'], reverse = True)

def get_latest_available_revision(env, version_directory_format, max_revision, **override_args):
    ''' Returns the last revision of a file list '''
    revisions = list_all_revisions(env, version_directory_format, **override_args)
    for version_info in revisions:
        revision = version_info['revision']
        if max_revision is None or int(revision) <= int(max_revision):
            logging.debug('Found version %s', revision)
            return revision

    raise Exception('No version <= %s found. Candidates were: %s' % (max_revision, ' '.join(revisions)))

