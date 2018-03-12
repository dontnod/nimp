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

import datetime
import fnmatch
import glob
import logging
import os
import re

import requests

import nimp.system


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
        archive_location_format = nimp.system.sanitize_path(archive_location_format)
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
    logging.debug("Extracting info from %s", archive_path)
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
        nimp.system.safe_makedirs(os.path.dirname(memo_path))
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
