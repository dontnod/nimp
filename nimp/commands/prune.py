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
''' Command to delete old files from a directory based on a file defining a
    set of rules '''

import datetime
import logging
import os
import os.path
import re
import shutil
import stat

import nimp.build
import nimp.command
import nimp.environment

class Prune(nimp.command.Command):
    ''' Cleans a directory using a rule file. '''
    def __init__(self):
        super(Prune, self).__init__()

    def configure_arguments(self, env, parser):
        parser.add_argument('file',
                            help     = 'Configuration file ',
                            metavar  = '<file>')

        parser.add_argument('--dry',
                            help    = 'Only list operation, don\'t execute them.',
                            default = False,
                            action  = "store_true")
        return True

    def run(self, env):
        prune_policy_path = env.file
        prune_policy_conf = nimp.environment.read_config_file(prune_policy_path)
        prune_directory = os.path.dirname(prune_policy_path)
        if not prune_policy_conf:
            logging.error("Error while loading prune policy configuration %s", prune_policy_path)
            return False

        if 'policies' not in prune_policy_conf:
            logging.error("No policiy declaration found in prune_policy.conf, doing nothing")
            return True

        sym_transactions = None
        if 'symsrv' in prune_policy_conf:
            sym_transactions = nimp.build.get_symbol_transactions(prune_policy_conf['symsrv'])

        success = True
        for policy in prune_policy_conf['policies']:
            success &= _prune(env, prune_directory, policy, sym_transactions)

        if sym_transactions is not None:
            for sym_trans in sym_transactions:
                if 'used' not in sym_trans or not sym_trans['used']:
                    logging.debug("Deleting unused symbol transaction %s...", sym_trans['comment'])
                    if not env.dry:
                        success &= nimp.build.delete_symbol_transaction(prune_policy_conf['symsrv'], sym_trans['id'])

        return success

def _prune(env, prune_directory, policy, sym_transactions):
    shutil_error = False
    #pylint: disable=unused-argument
    def _on_shutil_error(_, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        try:
            os.remove(path)
        except IOError as ex:
            logging.warning("Error deleting file %s : %s", path, ex)
            # shutil_error = True

    for pattern in policy['patterns']:
        logging.info("Pruning revisions matching %s", os.path.join(prune_directory, pattern))
        # TODO : Better than overriding the platform here, we maybe could give arguments here to filter the revisions to delete
        revs_infos = nimp.system.list_all_revisions(env, os.path.join(prune_directory, pattern), platform = '*')
        rev_ids = {}
        for rev_infos in revs_infos:
            rev_type = rev_infos['rev_type']
            if rev_type not in rev_ids:
                rev_ids[rev_type] = 1

            if not _should_keep_revision(policy, rev_ids[rev_type], rev_infos):
                if not env.dry:
                    shutil.rmtree(nimp.system.sanitize_path(rev_infos['path']), onerror = _on_shutil_error)
            else:
                rev_ids[rev_type] += 1
                if 'sym_comment_pattern' in policy:
                    _mark_used_symbols(rev_infos, policy['sym_comment_pattern'], sym_transactions)

    return not shutil_error

def _should_keep_revision(policy, rev_id, rev_infos):

    rev_path = rev_infos['path']
    rev_date = rev_infos['creation_date']

    if 'min_revisions' in policy and policy['min_revisions'] >= rev_id:
        logging.info('Keeping %s (rev_id = %s, min_revisions = %s)',
                     rev_path, rev_id, policy['min_revisions'])
        return True

    revision_age = datetime.datetime.now() - rev_date
    if 'min_age' in policy and policy['min_age'] >= revision_age:
        logging.debug('Keeping %s (created = %s, min_age = %s)',
                      rev_path, rev_date, policy['min_age'])
        return True

    keep_file_path = os.path.join(rev_path, 'dont_prune_me')
    if os.path.exists(keep_file_path):
        logging.debug('Keeping %s (found “dont_prune_me” file)', rev_path)
        return True

    if 'max_revisions' in policy and policy['max_revisions'] < rev_id:
        logging.debug('Deleting %s (rev_id = %s, max_revisions = %s).',
                      rev_path, rev_id, policy['max_revisions'])
        return False

    if 'max_age' in policy and policy['max_age'] < revision_age:
        logging.debug('Deleting %s (created = %s, max_age = %s)',
                      rev_path, rev_date, policy['max_age'])
        return False

    logging.debug('Keeping %s (no rule applies)', rev_path)
    return True

def _mark_used_symbols(rev_infos, sym_comment_pattern, sym_transactions):
    sym_comment_pattern = sym_comment_pattern.format(**rev_infos)
    sym_comment_re = re.compile(sym_comment_pattern)
    for transaction in sym_transactions:
        if sym_comment_re.match(transaction['comment']):
            logging.debug(('Marking symbol transaction %s as used due to'
                           'revision %s referencing it.'),
                          transaction['comment'], rev_infos['path'])
            transaction['used'] = True

