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

''' Provides functions for build artifacts '''
import copy
import hashlib
import glob
import json
import logging
import os
import platform
import re
import shutil
import stat
import time
import zipfile

import requests

import nimp.system
import nimp.utils.git


if platform.system() != 'Windows':
    try:
        import magic
    except ImportError:
        magic = None

try:
    import BitTornado.Meta.Info
    import BitTornado.Meta.BTTree
    import BitTornado.Meta.bencode
except ImportError as exception:
    BitTornado = None


def list_artifacts(artifact_pattern, format_arguments, api_context):
    ''' List all artifacts and their revision using the provided pattern after formatting '''

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
            group_revision = artifact_match.group('revision')
            sortable_revision = copy.deepcopy(group_revision)
            if api_context:
                sortable_revision = nimp.utils.git.get_gitea_commit_timestamp(api_context, group_revision)
            if sortable_revision is not None:
                artifact = {
                    'revision': group_revision,
                    'sortable_revision': sortable_revision,
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
        # scandir is way faster than listdir, especially via vpn
        # and is available in std os lib since python v3.5+
        for file_name in os.scandir(source):
            file_path = source + '/' + file_name.name
            if file_name.is_dir():
                all_files.append(file_path + '/')
                if recursive:
                    all_files.extend(_list_files(file_path, True))
            else:
                all_files.append(file_path)


    return all_files


def download_artifact(workspace_directory, artifact_uri):
    ''' Download an artifact to the workspace '''

    download_directory = os.path.join(workspace_directory, '.nimp', 'downloads')
    artifact_name = os.path.basename(artifact_uri.rstrip('/'))
    if artifact_name.endswith('.zip'):
        artifact_name = artifact_name[:-4]
    # Use a hash instead of the artifact name to reduce path length
    artifact_hash = hashlib.md5(artifact_name.encode('utf-8')).hexdigest()
    local_artifact_path = os.path.join(download_directory, artifact_hash[:10])

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
    ''' Install an artifact in the workspace '''

    if not os.path.exists(artifact_path):
        raise ValueError('Artifact does not exist: ' + artifact_path)

    if platform.system() != 'Windows' and magic is None:
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
    if platform.system() == 'Windows':
        return

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

def _try_rename(src, dst, max_attempts=5, retry_delay=2):
    def _rename():
        os.rename(src, dst)
    nimp.system.try_execute(_rename, OSError, attempt_maximum=max_attempts, retry_delay=retry_delay)

def create_artifact(artifact_path, file_collection, archive, compress, dry_run):
    ''' Create an artifact '''

    if os.path.isfile(artifact_path + '.zip') or os.path.isdir(artifact_path):
        raise ValueError('Artifact already exists: %s' % artifact_path)

    if not dry_run:
        if os.path.isfile(artifact_path + '.zip.tmp'):
            os.remove(artifact_path + '.zip.tmp')
        if os.path.isdir(artifact_path + '.tmp'):
            shutil.rmtree(artifact_path + '.tmp')

    if dry_run:
        for source, destination in file_collection:
            if os.path.isdir(source):
                continue
            logging.debug('Adding %s as %s', source, destination)

    elif archive:
        archive_path = artifact_path + '.zip'
        compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
        with zipfile.ZipFile(archive_path + '.tmp', 'w', compression = compression) as archive_file:
            for source, destination in file_collection:
                if os.path.isdir(source):
                    continue
                logging.debug('Adding %s as %s', source, destination)
                archive_file.write(source, destination)
        with zipfile.ZipFile(archive_path + '.tmp', 'r') as archive_file:
            if archive_file.testzip():
                raise OSError('Archive is corrupted')
        logging.debug('Renaming %s to %s' % (archive_path + '.tmp', artifact_path))
        shutil.move(archive_path + '.tmp', archive_path)

    else:
        artifact_path_tmp = artifact_path + '.tmp'
        for source, destination in file_collection:
            if os.path.isdir(source):
                continue
            logging.debug('Adding %s as %s', source, destination)
            destination = os.path.join(artifact_path_tmp, destination)
            os.makedirs(os.path.dirname(destination), exist_ok = True)
            shutil.copyfile(source, destination)
        logging.debug('Try : renaming %s to %s' % (artifact_path_tmp, artifact_path))
        try:
            # Sometimes shutils.move copies files instead of moving them, maybe
            # because of issues with network shares, so we try os.rename first.
            _try_rename(artifact_path_tmp, artifact_path, max_attempts=30, retry_delay=2)
            if os.path.exists(artifact_path):
                logging.debug("Succes : renaming %s to %s" % (artifact_path_tmp, artifact_path))
        except Exception as ex:
            logging.debug('Renaming failed (%s), trying alternate method' % (ex))
            shutil.move(artifact_path_tmp, artifact_path)


def create_torrent(artifact_path, announce, dry_run):
    ''' Create a torrent for an existing artifact '''

    if BitTornado is None:
        raise ImportError('Required module "BitTornado" is not available')

    torrent_path = artifact_path + '.torrent'
    if not dry_run:
        if os.path.isfile(torrent_path + '.tmp'):
            os.remove(torrent_path + '.tmp')
        if os.path.isfile(torrent_path):
            os.remove(torrent_path)

    if os.path.isfile(artifact_path + '.zip'):
        torrent_name = os.path.basename(artifact_path + '.zip')
        all_torrent_trees = [ BitTornado.Meta.BTTree.BTTree(artifact_path + '.zip', [ os.path.basename(artifact_path + '.zip') ]) ]
    elif os.path.isdir(artifact_path):
        torrent_name = os.path.basename(artifact_path)
        all_torrent_trees = []
        for source in glob.glob(os.path.join(artifact_path, '**'), recursive = True):
            if os.path.isfile(source):
                destination = os.path.relpath(source, artifact_path)
                all_torrent_trees.append(BitTornado.Meta.BTTree.BTTree(source, os.path.normpath(destination).split(os.path.sep)))
    else:
        raise FileNotFoundError('Artifact not found: %s' % artifact_path)

    torrent_info = BitTornado.Meta.Info.Info(torrent_name, sum(tree.size for tree in all_torrent_trees))
    for torrent_tree in all_torrent_trees:
        torrent_tree.addFileToInfos([torrent_info])
        BitTornado.Meta.Info.check_info(torrent_info)

    torrent_metainfo_parameters = { 'announce': announce }
    torrent_metainfo_parameters = { key: value for key, value in torrent_metainfo_parameters.items() if value is not None }
    torrent_metainfo = BitTornado.Meta.Info.MetaInfo(info = torrent_info, **torrent_metainfo_parameters)

    if not dry_run:
        with open(torrent_path + '.tmp', 'wb') as torrent_file:
            torrent_file.write(BitTornado.Meta.bencode.bencode(torrent_metainfo))
        shutil.move(torrent_path + '.tmp', torrent_path)


def create_hash(artifact_path, hash_method, dry_run):
    artifact_full_path = _find_artifact(artifact_path)
    if not artifact_full_path:
        raise FileNotFoundError(f'Artifact not found: {artifact_path}')

    file_hash = get_file_hash(artifact_full_path, hash_method)
    if not file_hash:
        raise ValueError(f'Something went wrong while hashing {artifact_full_path}')

    if not dry_run:
        with TempArtifact(f'{artifact_full_path}.hash', 'w', force=True) as fh:
            json.dump({hash_method: file_hash}, fh)


def get_file_hash(file_path, hash_method):
    ''' helper function to parse potentially big files '''
    assert getattr(hashlib, hash_method)()
    hash_lib = getattr(hashlib, hash_method)()

    _BLOCK_SIZE = 65536

    with open(file_path, 'rb') as fh:
        file_buffer = fh.read(_BLOCK_SIZE)
        while len(file_buffer) > 0:
            hash_lib.update(file_buffer)
            file_buffer = fh.read(_BLOCK_SIZE)
    file_hash = hash_lib.hexdigest()

    logging.debug(f"{file_path} {hash_method}: {file_hash}")
    return file_hash


# TODO (l.cahour): this is workaround the fact we don't use artifact objects containing the info we need
def _find_artifact(artifact_path):
    if os.path.isfile(artifact_path + '.zip'):
        return artifact_path + '.zip'
    elif os.path.isdir(artifact_path):
        return artifact_path
    else:
        return None


# TODO (l.cahour): this is a naive first attempt at using a wrapper class to clean how we handle artifacts saving
#                  Try to make this better and use it everywhere else in the future
class TempArtifact(object):
    def __init__(self, file_path, mode, force=False):
        self.name = file_path
        self.temp = f'{file_path}.tmp'
        self.mode = mode
        self.force = force

    def __enter__(self):
        if self.force:
            self.clear()
        self.file_handle = open(self.temp, self.mode)
        return self.file_handle

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file_handle.close()
        self.save()

    def clear(self):
        if os.path.isfile(self.temp):
            os.remove(self.temp)
        if os.path.isfile(self.name):
            os.remove(self.name)

    def save(self):
        shutil.move(self.temp, self.name)
