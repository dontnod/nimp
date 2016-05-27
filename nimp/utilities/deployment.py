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
''' Deployment related stuff '''

import datetime
import glob
import logging
import os
import re
import shutil
import stat
import time

import nimp.utilities.system

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

