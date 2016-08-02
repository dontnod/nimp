# -*- coding: utf-8 -*-
# Copyright © 2014—2016 Dontnod Entertainment

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

import ctypes
import datetime
import fnmatch
import glob
import logging
import os
import os.path
import platform
import re
import shutil
import stat
import struct
import subprocess
import threading
import time
import importlib

import glob2

import nimp.environment

def is_windows():
    ''' Return True if the runtime platform is Windows, including MSYS '''
    return is_msys() or platform.system() == 'Windows'

def is_msys():
    ''' Returns True if the platform is msys. '''
    return platform.system()[0:7] == 'MSYS_NT'

def try_import(module_name):
    ''' Tries to import a module, return none if unavailable '''
    try:
        return importlib.import_module(module_name)
    except ImportError:
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
    logging.debug('Running "%s" in "%s"', ' '.join(command), os.path.abspath(directory))
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
    logging.debug('Running "%s" in "%s"', ' '.join(command), os.path.abspath(directory))

    if is_windows():
        _disable_win32_dialogs()
        debug_pipe = _OutputDebugStringLogger()

    # The bufsize = 1 is important; if we don’t bufferise the
    # output, we’re going to make the callee lag a lot.
    try:
        process = subprocess.Popen(command,
                                   cwd     = directory,
                                   stdout  = subprocess.PIPE,
                                   stderr  = subprocess.PIPE,
                                   stdin   = None,
                                   bufsize = 1)
    except FileNotFoundError as ex:
        logging.error(ex)
        return 1

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

    def _output_worker(in_pipe):
        # FIXME: it would be better to use while process.poll() == None
        # here, but thread safety issues in Python < 3.4 prevent it.
        while process:
            try:
                logger = logging.getLogger('child_processes')
                for line in iter(in_pipe.readline, ''):
                    # Try to decode as UTF-8 first; if it fails, try CP850 on
                    # Windows, or UTF-8 with error substitution elsewhere. If
                    # it fails again, try CP850 with error substitution.
                    try:
                        line = line.decode("utf-8")
                    except UnicodeError:
                        try:
                            if is_windows():
                                line = line.decode("cp850")
                            else:
                                line = line.decode("utf-8", errors='replace')
                        except UnicodeError:
                            line = line.decode("cp850", errors='replace')

                    if line == '':
                        break

                    logger.info(line.strip('\n').strip('\r'))

                # Sleep for 10 milliseconds if there was no data,
                # or we’ll hog the CPU.
                time.sleep(0.010)

            except ValueError:
                return

    log_thread_args = [ (process.stdout,),
                        (process.stderr,)]
    if is_windows():
        log_thread_args += [ (debug_pipe.output,) ]

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

    return process_return

def robocopy(src, dest):
    ''' 'Robust' copy. '''

    # Retry up to 5 times after I/O errors
    max_retries = 10

    src = sanitize_path(src)
    dest = sanitize_path(dest)

    logging.debug('Copying "%s" to "%s"', src, dest)

    if os.path.isdir(src):
        safe_makedirs(dest)
    elif os.path.isfile(src):
        dest_dir = os.path.dirname(dest)
        safe_makedirs(dest_dir)
        while True:
            try:
                if os.path.exists(dest):
                    os.chmod(dest, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
                shutil.copy2(src, dest)
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

def load_arguments(env):
    '''Sets default platform '''
    if not hasattr(env, 'platform') or env.platform is None:
        if is_windows():
            env.platform = 'win64'
        elif platform.system() == 'Darwin':
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

def list_all_revisions(env, version_directory_format, **override_args):
    ''' Lists all revisions based on directory pattern '''
    version_directory_format = sanitize_path(version_directory_format)
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

if is_windows():
    _KERNEL32 = ctypes.windll.kernel32 if hasattr(ctypes, 'windll') else None
    _KERNEL32.MapViewOfFile.restype = ctypes.c_void_p
    _KERNEL32.UnmapViewOfFile.argtypes = [ctypes.c_void_p]

    INVALID_HANDLE_VALUE = -1 # Should be c_void_p(-1).value but doesn’t work

    WAIT_OBJECT_0 = 0x00000000
    WAIT_OBJECT_1 = 0x00000001
    INFINITE      = 0xFFFFFFFF

    PAGE_READWRITE = 0x4

    FILE_MAP_READ = 0x0004

    SEM_FAILCRITICALERRORS = 0x0001
    SEM_NOGPFAULTERRORBOX  = 0x0002
    SEM_NOOPENFILEERRORBOX = 0x8000

    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_SYNCHRONIZE = 0x00100000

    def _disable_win32_dialogs():
        ''' Disable “Entry Point Not Found” and “Application Error” dialogs for
            child processes '''

        _KERNEL32.SetErrorMode(SEM_FAILCRITICALERRORS \
                            | SEM_NOGPFAULTERRORBOX \
                            | SEM_NOOPENFILEERRORBOX)

    class _OutputDebugStringLogger(threading.Thread):
        ''' Get output debug string from a process and writes it to a pipe '''
        def __init__(self):
            super().__init__()

            fd_in, fd_out = os.pipe()
            self.output = os.fdopen(fd_in, 'rb')
            self._pipe_in = os.fdopen(fd_out, 'wb')

            self._buffer_ev = _KERNEL32.CreateEventW(None, 0, 0, 'DBWIN_BUFFER_READY')
            self._data_ev = _KERNEL32.CreateEventW(None, 0, 0, 'DBWIN_DATA_READY')
            self._stop_ev = _KERNEL32.CreateEventW(None, 0, 0, None)
            self._bufsize = 4096

            self._mapping = _KERNEL32.CreateFileMappingW(INVALID_HANDLE_VALUE,
                                                         None,
                                                         PAGE_READWRITE,
                                                         0,
                                                         self._bufsize,
                                                         'DBWIN_BUFFER')

            self._buffer = _KERNEL32.MapViewOfFile(self._mapping,
                                                   FILE_MAP_READ,
                                                   0, 0,
                                                   self._bufsize)
            self._pid = None

        @staticmethod
        def _pid_to_winpid(pid):
            # In case we’re running in MSYS2 Python, the PID we got is actually an
            # internal MSYS2 PID, and the PID we want to watch is actually the WINPID,
            # which we retrieve in /proc
            try:
                return int(open("/proc/%d/winpid" % (pid,)).read(10))
            #pylint: disable=broad-except
            except Exception:
                return pid

        def attach(self, pid):
            ''' Sets the process pid from wich to capture output debug string '''
            self._pid = _OutputDebugStringLogger._pid_to_winpid(pid)
            logging.debug("Attached to process %d (winpid %d)", pid, self._pid)

        def run(self):
            pid_length = 4
            data_length = self._bufsize - pid_length

            # Signal that the buffer is available
            _KERNEL32.SetEvent(self._buffer_ev)

            events = [self._data_ev, self._stop_ev]
            while True:
                result = _KERNEL32.WaitForMultipleObjects(len(events),
                                                          (ctypes.c_void_p * len(events))(*events),
                                                          0,
                                                          INFINITE)
                if result == WAIT_OBJECT_0:
                    pid_data = ctypes.string_at(self._buffer, pid_length)
                    pid, = struct.unpack('I', pid_data)
                    data = ctypes.string_at(self._buffer + pid_length, data_length)

                    # Signal that the buffer is available
                    _KERNEL32.SetEvent(self._buffer_ev)

                    if pid != self._pid:
                        continue

                    self._pipe_in.write(data[:data.index(0)])
                    self._pipe_in.flush()

                elif result == WAIT_OBJECT_1:
                    break

                else:
                    time.sleep(0.100)

        def stop(self):
            ''' Stops this OutputDebugStringLogger '''
            _KERNEL32.SetEvent(self._stop_ev)
            self.join()
            _KERNEL32.UnmapViewOfFile(self._buffer)
            _KERNEL32.CloseHandle(self._mapping)
            self._pipe_in.close()

            self.output.close()

    class NimpMonitor(threading.Thread):
        ''' Watchdog killing child processes when nimp ends '''
        def __init__(self):
            super().__init__()
            self._watcher_event_handle = _KERNEL32.CreateEventW(None, 0, 0, None)
            if self._watcher_event_handle == 0:
                logging.error("cannot create event")
            self._nimp_handle = _KERNEL32.OpenProcess(PROCESS_SYNCHRONIZE | PROCESS_QUERY_INFORMATION, False, os.getppid())
            if self._nimp_handle == 0:
                logging.error("cannot open nimp process")

        def run(self):
            events = [self._nimp_handle, self._watcher_event_handle]
            while True:
                result = _KERNEL32.WaitForMultipleObjects(len(events), (ctypes.c_void_p * len(events))(*events), 0, INFINITE)
                if result == WAIT_OBJECT_0:
                    logging.debug("Parent nimp.exe is not running anymore: current python process and its subprocesses are going to be killed")
                    call_process('.', ['taskkill', '/F', '/T', '/PID', str(os.getpid())])
                    break
                elif result == WAIT_OBJECT_1:
                    break

        def stop(self):
            ''' Stops this monitor '''
            _KERNEL32.CloseHandle(self._nimp_handle)
            _KERNEL32.SetEvent(self._watcher_event_handle)

def _identity_mapper(src, dest):
    yield src, dest

