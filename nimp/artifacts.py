# -*- coding: utf-8 -*-
# Copyright © 2014-2018 Dontnod Entertainment

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
''' Provides functions for build artifacts '''

import copy
import logging
import os
import re
import shutil
import stat
import zipfile

import requests

import nimp.sys.platform
import nimp.system

magic = nimp.system.try_import('magic')


def list_artifacts(artifact_pattern, format_arguments):
    ''' Lists all artifacts and their revision using the provided pattern after formatting '''

    format_arguments = copy.deepcopy(format_arguments)
    format_arguments['revision'] = '{revision}'

    artifact_pattern = artifact_pattern.format(**format_arguments)
    artifact_source = nimp.system.sanitize_path(os.path.dirname(artifact_pattern))
    artifact_escaped_name = re.escape(os.path.basename(artifact_pattern)).replace(r'\{revision\}', '{revision}')
    artifact_regex = re.compile(r'^' + artifact_escaped_name.format(revision = r'(?P<revision>[a-zA-Z0-9]+)') + r'(.zip)?$')

    all_files = _list_files(artifact_source, False)
    all_artifacts = []
    for file_uri in all_files:
        file_name = os.path.basename(file_uri.rstrip('/'))
        artifact_match = artifact_regex.match(file_name)
        if artifact_match:
            artifact = {
                'revision': artifact_match.group('revision'),
                'uri': file_uri,
            }
            all_artifacts.append(artifact)
    return all_artifacts


def _list_files(source, recursive):
    all_files = []
    source = source.rstrip('/')

    if source.startswith('http://') or source.startswith('https://'):
        source_request = requests.get(source)
        source_request.raise_for_status()
        file_regex = re.compile(r'<a href="(?P<file_name>[^"/\\\?]+/?)">')

        for source_line in source_request.text.splitlines():
            file_match = file_regex.search(source_line)
            if file_match:
                file_path = source + '/' + file_match.group('file_name')
                all_files.append(file_path)
                if recursive and file_path.endswith('/'):
                    all_files.extend(_list_files(file_path, True))

    else:
        for file_name in os.listdir(source):
            file_path = source + '/' + file_name
            if os.path.isdir(file_path):
                all_files.append(file_path + '/')
                if recursive:
                    all_files.extend(_list_files(file_path, True))
            else:
                all_files.append(file_path)

    return all_files


def download_artifact(workspace_directory, artifact_uri):
    ''' Downloads an artifact to the workspace '''

    download_directory = os.path.join(workspace_directory, '.nimp', 'downloads')
    artifact_name = os.path.basename(artifact_uri.rstrip('/'))
    local_artifact_path = os.path.join(download_directory, artifact_name)
    if local_artifact_path.endswith('.zip'):
        local_artifact_path = local_artifact_path[:-4]

    if os.path.exists(local_artifact_path + '.zip'):
        os.remove(local_artifact_path + '.zip')
    if os.path.exists(local_artifact_path):
        shutil.rmtree(local_artifact_path)

    if artifact_uri.endswith('.zip'):
        _download_file(artifact_uri, local_artifact_path + '.zip')
        _extract_archive(local_artifact_path + '.zip', local_artifact_path)
        os.remove(local_artifact_path + '.zip')
    else:
        artifact_uri = artifact_uri.rstrip('/') + '/'
        all_files = [ uri for uri in _list_files(artifact_uri, True) if not uri.endswith('/') ]
        for file_uri in all_files:
            file_path = file_uri[ len(artifact_uri) : ]
            _download_file(file_uri, os.path.join(local_artifact_path, file_path))

    return local_artifact_path


def _download_file(file_uri, output_path):
    if os.path.exists(output_path):
        os.remove(output_path)
    output_directory = os.path.dirname(output_path)
    if not os.path.isdir(output_directory):
        os.makedirs(output_directory)

    if file_uri.startswith('http://') or file_uri.startswith('https://'):
        file_request = requests.get(file_uri, stream = True)
        file_request.raise_for_status()
        with open(output_path, 'wb') as output_file:
            shutil.copyfileobj(file_request.raw, output_file)
    else:
        shutil.copyfile(file_uri, output_path)


def _extract_archive(archive_path, output_path):
    if os.path.exists(output_path):
        shutil.rmtree(output_path)

    with zipfile.ZipFile(archive_path) as archive:
        archive_file_list = archive.namelist()
        is_archive_package = all(file_name.endswith('.zip') for file_name in archive_file_list)
        archive_file_list = archive.namelist()
        archive.extractall(output_path)

    if is_archive_package:
        for inner_archive_path in archive_file_list:
            inner_archive_path = os.path.join(output_path, inner_archive_path)
            with zipfile.ZipFile(inner_archive_path) as inner_archive:
                inner_archive.extractall(output_path)
            os.remove(inner_archive_path)


def install_artifact(artifact_path, destination_directory):
    ''' Installs an artifact in the workspace '''

    if not os.path.exists(artifact_path):
        raise ValueError('Artifact does not exist: ' + artifact_path)

    if not nimp.sys.platform.is_windows() and magic is None:
        logging.warning('python-magic is not available, executable permissions will not be set')

    all_files = [ file_path for file_path in _list_files(artifact_path, True) if os.path.isfile(file_path) ]
    for source in all_files:
        destination = os.path.join(destination_directory, source[ len(artifact_path) + 1 : ])
        logging.debug('Installing %s to %s', source, destination)
        if os.path.exists(destination):
            os.remove(destination)
        if not os.path.isdir(os.path.dirname(destination)):
            os.makedirs(os.path.dirname(destination))
        shutil.move(source, destination)
        _try_make_executable(destination)


def _try_make_executable(file_path):
    if magic is not None:
        file_type = magic.from_file(file_path)
        if isinstance(file_type, bytes):
            # Older versions of python-magic return bytes instead of a string
            file_type = file_type.decode('ascii')

        if 'executable' in file_type or 'script' in file_type:
            try:
                file_stat = os.stat(file_path)
                os.chmod(file_path, file_stat.st_mode | stat.S_IEXEC)
            except OSError as exception:
                logging.warning('Failed to make file executable: %s (FilePath: %s)', exception, file_path)
