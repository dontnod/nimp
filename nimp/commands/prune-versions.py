# -*- coding: utf-8 -*-

import datetime

from nimp.commands._command import *
from nimp.utilities.ue3 import *
from nimp.utilities.ue4 import *
from nimp.utilities.deployment import *
from nimp.utilities.file_mapper import *
from nimp.utilities.symbols import *

#-------------------------------------------------------------------------------
class PruneVersionsCommand(Command):
    def __init__(self):
        Command.__init__(self, 'prune-versions', 'Prune old versions')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('--dry',
                            help    = 'Only list operation, don\'t execute them.',
                            default = False,
                            action  = "store_true")
        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        directories_to_wipe = []
        symbol_transactions = get_symbol_transactions(env)

        if not symbol_transactions:
            return False

        referenced_transactions = set()
        now = datetime.datetime.now()

        for directory, settings in env.prune_policy.items():
            log_notification("Listing version to wipe from of {0}", directory)
            revisions_infos = list_all_revisions(env, getattr(env, directory))
            nb_revisions = len(revisions_infos)

            if 'min_revisions' in settings and int(settings['min_revisions']) >= nb_revisions:
                log_notification("Found only {0} revisions in this directory : keeping them all", nb_revisions)
                continue
            for revision_info in revisions_infos:
                revision_age = now - revision_info['creation_date']

                if settings['max_age'] < revision_age:
                    log_verbose("Revision in {0} is {1} old : wipping", revision_info['path'], revision_age)
                    directories_to_wipe.append(revision_info['path'])

                elif 'sym_comment_pattern' in settings:
                    sym_comment_pattern = env.format(settings['sym_comment_pattern'], **revision_info)
                    sym_comment_re = re.compile(sym_comment_pattern)

                    for transaction in symbol_transactions:
                        if sym_comment_re.match(transaction['comment']):
                            log_verbose("Version {0} is to keep and reference symbol transaction {1} : marking transaction as referenced.", revision_info['revision'], transaction['id'])
                            referenced_transactions.add(transaction['id'])

        transactions_to_delete = set([transaction['id'] for transaction in symbol_transactions])
        transactions_to_delete -= referenced_transactions

        shutil_error = False
        def _on_shutil_error(function, path, excinfo):
            os.chmod(path, stat.S_IWRITE)
            try:
                os.remove(path)
            except Exception as ex:
                log_error("Error deleting file {0} : {1}", path, ex)
                shutil_error = True

        for path in directories_to_wipe:
            log_notification("Deleting {0}...", path)
            if not env.dry:
                shutil.rmtree(path, onerror = _on_shutil_error)

        if shutil_error:
            return False

        for id in transactions_to_delete:
            log_notification("Deleting transaction {0}...", id)
            if not env.dry:
                if not delete_symbol_transaction(env, id):
                    return False

        return True