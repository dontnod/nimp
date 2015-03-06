# -*- coding: utf-8 -*-

import os
import os.path
import re
import subprocess
import sys
import threading
import time
import tempfile

from nimp.utilities.processes import *
from nimp.utilities.paths     import *


CREATE_CHANGELIST_FORM_TEMPLATE = "\
Change: new\n\
User:   {user}\n\
Client: {workspace}\n\
Status: pending\n\
Description:\n\
        {description}"

#-------------------------------------------------------------------------------
def p4_add(cl_number, path):
    return _p4_run_command(".", ["p4", "-z", "tag", "add", "-c", cl_number, path])

#-------------------------------------------------------------------------------
def p4_clean_workspace():
    result = True
    # On ignore le retour de cette commande, parce qu'elle peut potentiellement
    # foirer si des fichiers on été addés puis revert, et j'ai pas trouvé de
    # solution simple pour y remédier avec cette daube de P4.
    _p4_run_command(".", ["p4", "-z", "tag", "revert", "//..."]) is not None

    pending_changelists = p4_get_pending_changelists()

    for cl_number in pending_changelists:
        log_notification("Deleting changelist {0}", cl_number)
        result = result and p4_delete_changelist(cl_number)

    return result

#-------------------------------------------------------------------------------
def p4_create_config_file(port, user, password, client):
    log_notification("Creating .p4config file")
    p4_config_template = "\
P4USER={user}\n\
P4PORT={port}\n\
P4PASSWD={password}\n\
P4CLIENT={client}\n"
    p4_config = p4_config_template.format(port     = port,
                                          user     = user,
                                          password = password,
                                          client   = client)

    with open(".p4config", "w") as p4_config_file:
        p4_config_file.write(p4_config)

    return True

#-------------------------------------------------------------------------------
def p4_delete_changelist(cl_number):
    output = _p4_run_command(".", ["p4", "-z", "tag", "change", "-d", cl_number])
    return output is not None

#-------------------------------------------------------------------------------
def p4_edit(cl_number, file):
    return _p4_run_command(".", ["p4", "-z", "tag", "edit", "-c", cl_number, file])

#-------------------------------------------------------------------------------
def p4_get_changelist_description(cl_number):
    return _p4_parse_command_output(".", ["p4", "-z", "tag", "describe", cl_number], "\.\.\. desc (.*)")

#-------------------------------------------------------------------------------
def p4_get_last_synced_changelist():
    workspace = p4_get_workspace()

    if workspace is None:
        return None

    cl_number = _p4_parse_command_output(".", ["p4", "-z", "tag", "changes", "-s", "submitted", "-m1", "@{0}".format(workspace)], "\.\.\. change ([0-9]*)")

    if(cl_number is None):
        return None

    return cl_number

#-------------------------------------------------------------------------------
def p4_get_or_create_changelist(description):
    pending_changelists = p4_get_pending_changelists()

    for cl_number in pending_changelists:
        pending_cl_desc = p4_get_changelist_description(cl_number)

        if pending_cl_desc is None:
            return None

        if description.lower() == pending_cl_desc.lower():
            return cl_number

    user = p4_get_user()
    change_list_form = CREATE_CHANGELIST_FORM_TEMPLATE.format(user          = user,
                                                              workspace     = p4_get_workspace(),
                                                              description   = description)

    return _p4_parse_command_output(".", ["p4", "-z", "tag","change", "-i"], "Change ([0-9]*) created\.", change_list_form)

#-------------------------------------------------------------------------------
def p4_get_pending_changelists():
    return _p4_parse_command_output_list(".", ["p4", "-z", "tag", "changes", "-c", p4_get_workspace(), "-s", "pending"], "\.\.\. change ([0-9]*)")

#-------------------------------------------------------------------------------
def p4_get_user():
    return _p4_parse_command_output(".", ["p4", "-z", "tag", "user", "-o"], "^\.\.\. User (.*)$")

#-------------------------------------------------------------------------------
def p4_get_workspace():
    return _p4_parse_command_output(".", ["p4", "-z", "tag", "info"], "^\.\.\. clientName (.*)$")

#-------------------------------------------------------------------------------
def p4_is_file_versioned(file_path):
    result, output, error = capture_process_output(".", ["p4", "-z", "tag", "fstat", file_path])
    # Il faut checker que le fichier a pas été ajouté puis delete
    if re.search("\.\.\.\s*headAction\s*delete", output) is not None:
        return False
    return not "no such file(s)" in error

#-------------------------------------------------------------------------------
def p4_reconcile(cl_number, path):
    if os.path.isdir(path):
        path = path + "/..."

    if _p4_run_command(".", ["p4", "-z", "tag", "reconcile", "-c", cl_number, path]) is None:
            return False
    return True

#-------------------------------------------------------------------------------
def p4_revert_changelist(cl_number):
    return _p4_run_command(".", ["p4", "-z", "tag", "revert", "-c", cl_number, "//..."]) is not None

#-------------------------------------------------------------------------------
def p4_revert_unchanged(cl_number):
    return _p4_run_command(".", ["p4", "-z", "tag", "revert", "-a", "-c", cl_number, "//..."]) is not None

#-------------------------------------------------------------------------------
def p4_submit(cl_number):
    return _p4_run_command(".", ["p4", "-z", "tag", "submit", "-f", "revertunchanged", "-c", cl_number]) is not None

#-------------------------------------------------------------------------------
def p4_sync(cl_number = None):
    p4_command = ["p4", "-z", "tag", "sync"]

    if cl_number is not None:
        p4_command = p4_command + ["@{0}".format(cl_number)]

    return _p4_run_command(".", p4_command) is not None

#-------------------------------------------------------------------------------
def p4_transaction(cl_description, submit_on_success = False, revert_unchanged = True, add_not_versioned_files = True):
    return _PerforceTransaction(cl_description, submit_on_success, revert_unchanged, add_not_versioned_files)

#-------------------------------------------------------------------------------
class _PerforceTransaction:
    #---------------------------------------------------------------------------
    def __init__(self,
                 change_list_description,
                 submit_on_success          = False,
                 revert_unchanged           = True,
                 add_not_versioned_files    = True):
        self._change_list_description   = change_list_description
        self._success                   = True
        self._cl_number                 = None
        self._submit_on_success         = submit_on_success
        self._revert_unchanged          = revert_unchanged
        self._add_not_versioned_files   = add_not_versioned_files
        self._paths                     = []

    #---------------------------------------------------------------------------
    def __enter__(self):
        self._cl_number = p4_get_or_create_changelist(self._change_list_description)

        if self._cl_number is None:
            self._success = False
            raise Exception()

        return self

    #---------------------------------------------------------------------------
    def add(self, path):
        if path in self._paths:
            return

        self._paths.append(path)
        if p4_is_file_versioned(path):
           if p4_edit(self._cl_number, path):
              return True
        elif not self._add_not_versioned_files:
            return True
        elif p4_add(self._cl_number, path):
             return True

        log_error("An error occured while adding file to perforce transaction")
        self._success = False

        return False

    #---------------------------------------------------------------------------
    def abort(self):
        self._success = False

    #---------------------------------------------------------------------------
    def __exit__(self, type, value, trace):
        if value is not None:
            raise value

        if not self._success and self._cl_number is not None:
            log_verbose("P4 transaction aborted, reverting and deleting CLs...")
            p4_revert_changelist(self._cl_number)
            p4_delete_changelist(self._cl_number)
        elif self._cl_number is not None:
            if self._revert_unchanged:
                log_verbose("Reverting unchanged files...")
                if not p4_revert_unchanged(self._cl_number):
                    return False
            if self._submit_on_success:
                log_verbose("Committing result...")
                return p4_submit(self._cl_number)
        else:
            log_error("An error occured while entering perforce transaction, so not doing anything here.")
        return True

#-------------------------------------------------------------------------------
def _p4_run_command(directory, command, input = None, log_errors = True):
    log_verbose("Perforce : {0}", " ".join(command))
    result, output, error = capture_process_output(directory, command, input)
    if( result != 0 or error != ''):
        if log_errors:
            log_error("Perforce error : {1}", input, error.rstrip('\r\n'))
        return None
    return output

#-------------------------------------------------------------------------------
def _p4_parse_command_output(directory, command, pattern, input = None, log_errors = True):
    output = _p4_run_command(directory, command, input, log_errors)

    if output is None:
        return None

    match = re.search(pattern, output, re.MULTILINE)

    if(match is None):
        if log_errors:
            log_error("Error while parsing p4 command \'{0}\' output (got {1})", " ".join(command), output)
        return None

    result = match.group(1)
    result = result.strip()
    return result

#-------------------------------------------------------------------------------
def _p4_parse_command_output_list(directory, command, pattern, input = None, log_errors = True):
    output = _p4_run_command(directory, command, input, log_errors)

    if output is None:
        return None

    matches = list(re.finditer(pattern, output, re.MULTILINE))

    result = []
    for match in matches:
        match_string = match.group(1)
        match_string = match_string.strip()
        result.append(match_string)
    return result
