# -*- coding: utf-8 -*-

from datetime import date

import os
import stat
import os.path
import tempfile;
import shutil
import stat
import glob
import fnmatch
import datetime
import re
import contextlib
import pathlib

from nimp.utilities.perforce import *
from nimp.utilities.file_mapper import *
from nimp.utilities.hashing import *
from nimp.utilities.paths import *

#---------------------------------------------------------------------------
def list_all_revisions(env, version_directory_format, **override_args):
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

    format_args.update({'revision' : '(?P<revision>\d+)',
                        'platform'  : '(?P<platform>\w+)',
                        'dlc' : '(?P<dlc>\w+)',
                        'configuration' : '(?P<configuration>\w+)'})

    log_verbose('Looking for latest version in {0}…', version_directory_format)

    for version_directory in glob.glob(version_directories_glob):
        version_directory = version_directory.replace('\\', '/')
        version_regex = version_directory_format.format(**format_args)

        rev_match = re.match(version_regex, version_directory)

        if rev_match is not None:
            rev_infos = rev_match.groupdict()
            rev_infos['path'] = version_directory
            rev_infos['creation_date'] = datetime.fromtimestamp(os.path.getctime(version_directory))

            if not 'platform' in rev_infos:
                rev_infos['platform'] = "*"
            if not 'dlc' in rev_infos:
                rev_infos['dlc'] = "*"
            if not 'configuration' in rev_infos:
                rev_infos['configuration'] = "*"

            rev_infos['rev_type'] = '{dlc}_{platform}_{configuration}'.format(**rev_infos)
            revisions += [rev_infos]

    return sorted(revisions, key=lambda rev_infos: rev_infos['revision'], reverse = True)

#---------------------------------------------------------------------------
def get_latest_available_revision(env, version_directory_format, max_revision, **override_args):

    revisions = list_all_revisions(env, version_directory_format, **override_args)
    for version_info in revisions:
        revision = version_info['revision']
        if max_revision is None or int(revision) <= int(max_revision):
            log_verbose('Found version %s' % (revision))
            return revision

    raise Exception('No version <= %s found. Candidates were: %s' % (max_revision, ' '.join(revisions)))

#-------------------------------------------------------------------------------
def robocopy(src, dest):
    """ 'Robust' copy. """

    # Retry up to 5 times after I/O errors
    max_retries = 10

    src = sanitize_path(src)
    dest = sanitize_path(dest)

    log_verbose('Copying “{0}” to “{1}”', src, dest)

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
            except IOError as e:
                log_error('I/O error {0}: {1}', e.errno, e.strerror)
                max_retries -= 1
                if max_retries <= 0:
                    return False
                log_error('Retrying after 10 seconds ({0} retries left)', max_retries)
                time.sleep(10)
            except Exception as e:
                log_error('Copy error: {0}', e)
                return False
    else:
        log_error('Error: not such file or directory “{0}”', src)
        return False

    return True


#-------------------------------------------------------------------------------
def force_delete(path):
    """ 'Robust' delete. """

    path = sanitize_path(path)

    if os.path.exists(path):
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    os.remove(path)

#-------------------------------------------------------------------------------
def checkout(transaction):
    def _checkout_mapper(src, dest):
        if src is None:
            return True
        if os.path.isfile(src) and not transaction.add(src):
            return False
        return True

    return _checkout_mapper

#-------------------------------------------------------------------------------
def checkout_and_copy(transaction):
    def _checkout_and_copy_mapper(src, dest):
        if dest is None:
            raise Exception("checkout_and_copy() called on empty destination")
        if os.path.isfile(dest) and not transaction.add(dest):
            return False
        if not robocopy(src, dest):
            return False
        return True

    return _checkout_and_copy_mapper

