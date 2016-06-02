# -*- coding: utf-8 -*-

import datetime

import nimp.command
from nimp.unreal import *
from nimp.build import *
from nimp.environment import *

#-------------------------------------------------------------------------------
class PruneVersionsCommand(nimp.command.Command):
    def __init__(self):
        Command.__init__(self, 'prune-versions', 'Prune old versions')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('file',
                            help     = 'Configuration file ',
                            metavar  = '<FILE>')

        parser.add_argument('--dry',
                            help    = 'Only list operation, don\'t execute them.',
                            default = False,
                            action  = "store_true")
        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        prune_policy_path = env.file
        prune_policy_conf = read_config_file(prune_policy_path)
        prune_directory = os.path.dirname(prune_policy_path)
        if not prune_policy_conf:
            log_error("Error while loading prune policy configuration %s" % prune_policy_path)
            return False

        if not 'policies' in prune_policy_conf:
            log_warning("No policiy declaration found in prune_policy.conf, doing nothing")
            return True

        sym_transactions = None
        if 'symsrv' in prune_policy_conf:
            sym_transactions = get_symbol_transactions(prune_policy_conf['symsrv'])

        success = True
        for policy in prune_policy_conf['policies']:
            success &= _prune(env, prune_directory, policy, sym_transactions)

        if sym_transactions is not None:
            for sym_trans in sym_transactions:
                if not 'used' in sym_trans or not sym_trans['used']:
                    log_notification("Deleting unused symbol transaction {0}...", sym_trans['comment'])
                    if not env.dry:
                        success &= delete_symbol_transaction(prune_policy_conf['symsrv'], sym_trans['id'])

        return success

#---------------------------------------------------------------------------
def _prune(env, prune_directory, policy, sym_transactions):
    shutil_error = False
    def _on_shutil_error(function, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        try:
            os.remove(path)
        except Exception as ex:
            log_warning("Error deleting file {0} : {1}", path, ex)
            shutil_error = True

    for pattern in policy['patterns']:
        log_notification("Pruning revisions matching %s" % os.path.join(prune_directory, pattern.replace("{", "{{").replace("}", "}}")))
        # FIXME : Better than overriding the platform here, we maybe could give arguments here to filter the revisions to delete
        revs_infos = list_all_revisions(env, os.path.join(prune_directory, pattern), platform = '*')
        rev_ids = {}
        for rev_infos in revs_infos:
            rev_type = rev_infos['rev_type']
            if not rev_type in rev_ids:
                rev_ids[rev_type] = 1

            if not _should_keep_revision(policy, rev_ids[rev_type], rev_infos):
                if not env.dry:
                    shutil.rmtree(sanitize_path(rev_infos['path']), onerror = _on_shutil_error)
            else:
                rev_ids[rev_type] += 1
                if 'sym_comment_pattern' in policy:
                    _mark_used_symbols(rev_infos, policy['sym_comment_pattern'], sym_transactions)

    return not shutil_error

#---------------------------------------------------------------------------
def _should_keep_revision(policy, rev_id, rev_infos):

    rev_path = rev_infos['path']
    rev_date = rev_infos['creation_date']

    if 'min_revisions' in policy and policy['min_revisions'] >= rev_id:
        log_notification('Keeping {0} (rev_id = {1}, min_revisions = {2})',
                         rev_path, rev_id, policy['min_revisions'])
        return True

    revision_age = datetime.now() - rev_date
    if 'min_age' in policy and policy['min_age'] >= revision_age:
        log_verbose('Keeping {0} (created = {1}, min_age = {2})',
                    rev_path, rev_date, policy['min_age'])
        return True

    keep_file_path = os.path.join(rev_path, 'dont_prune_me')
    if os.path.exists(keep_file_path):
        log_verbose('Keeping {0} (found “dont_prune_me” file)', rev_path)
        return True

    if 'max_revisions' in policy and policy['max_revisions'] < rev_id:
        log_verbose('Deleting {0} (rev_id = {1}, max_revisions = {2}).',
                    rev_path, rev_id, policy['max_revisions'])
        return False

    if 'max_age' in policy and policy['max_age'] < revision_age:
        log_verbose('Deleting {0} (created = {1}, max_age = {2})',
                    rev_path, rev_date, policy['max_age'])
        return False

    log_verbose('Keeping {0} (no rule applies)', rev_path)
    return True

#---------------------------------------------------------------------------
def _mark_used_symbols(rev_infos, sym_comment_pattern, sym_transactions):
    sym_comment_pattern = sym_comment_pattern.format(**rev_infos)
    sym_comment_re = re.compile(sym_comment_pattern)
    for transaction in sym_transactions:
        if sym_comment_re.match(transaction['comment']):
            log_verbose("Marking symbol transaction {0} as used due to revision {1} referencing it.", transaction['comment'], rev_infos['path'])
            transaction['used'] = True
