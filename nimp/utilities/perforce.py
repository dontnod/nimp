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
from nimp.utilities.paths import *


CREATE_CHANGELIST_FORM_TEMPLATE = "\
Change: new\n\
User:   {user}\n\
Client: {workspace}\n\
Status: pending\n\
Description:\n\
        {description}"

#-------------------------------------------------------------------------------
def p4_add(cl_number, path):
    output = _p4_run_command(".", ["p4", "-z", "tag", "add", "-c", cl_number, path])
    return output is not None

#-------------------------------------------------------------------------------
def p4_clean_workspace():
    result = True
    _p4_run_command(".", ["p4", "-z", "tag", "revert", "//..."])
    pending_changelists = p4_get_pending_changelists()

    for cl_number in pending_changelists:
        log_notification("Deleting changelist {0}", cl_number)
        result = result and p4_delete_changelist(cl_number)

    return result

#-------------------------------------------------------------------------------
def p4_create_config_file(port, user, password, client):
    log_notification("Creating .p4config file")
    p4_config_template = """
P4USER={user}
P4PORT={port}
P4PASSWD={password}
P4CLIENT={client}
"""
    p4_config = p4_config_template.format(port     = port,
                                          user     = user,
                                          password = password,
                                          client   = client)

    with open(".p4config", "w") as p4_config_file:
        p4_config_file.write(p4_config)

    return True

#-------------------------------------------------------------------------------
def p4_delete(cl_number, path):
    output = _p4_run_command(".", ["p4", "-z", "tag", "delete", "-c", cl_number, path])
    return output is not None

#-------------------------------------------------------------------------------
def p4_delete_changelist(cl_number):
    output = _p4_run_command(".", ["p4", "-z", "tag", "change", "-d", cl_number])
    return output is not None

#-------------------------------------------------------------------------------
def p4_get_files_status(*files):
    files = list(files)
    for i in range(0, len(files)):
        if os.path.isdir(files[i]):
            files[i] = files[i] + "/..."

    result, output, error = capture_process_output(".", ["p4", "-x", "-", "-z", "tag","fstat"], '\n'.join(files), 'cp437')
    files_infos = output.strip().replace('\r', '').split('\n\n')
    edit_input = ""

    for file_info in files_infos:
        if "no such file(s)" in file_info or "file(s) not in client" in file_info:
            continue
        file_name_match   = re.search(r"\.\.\.\s*clientFile\s*(.*)", file_info)
        head_action_match = re.search(r"\.\.\.\s*headAction\s*(\w*)", file_info)
        action_match      = re.search(r"\.\.\.\s*action\s*(\w*)", file_info)

        if file_name_match is None:
            log_error("Got unexpected output from p4 fstat : {0}", file_info)
            continue

        file_name = file_name_match.group(1)

        if action_match is not None:
            action = action_match.group(1)
        else:
            action = None

        if head_action_match is not None:
            head_action = head_action_match.group(1)
        else:
            head_action = None

        yield (file_name, head_action, action)

#-------------------------------------------------------------------------------
def p4_edit(cl_number, *files):
    edit_input = ""

    for file_name, head_action, action in p4_get_files_status(*files):
        if head_action == "delete":
            log_verbose("Ignoring deleted file {0}", file_name)
            continue
        log_verbose("Adding file {0} to checkout", file_name)
        edit_input += file_name + "\n"

    output = _p4_run_command(".", ["p4", "-x", "-", "-z", "tag", "edit", "-c", cl_number], edit_input)
    return output is not None

#-------------------------------------------------------------------------------
def p4_reconcile(cl_number, *files):
    delete_input = ""
    for file_name, head_action, action in p4_get_files_status(*files):
        if action == "edit" and not os.path.exists(file_name):
            log_verbose("Manually reverting and deleting checkouted and missing file {0}", file_name)
            delete_input += file_name + "\n"

    if delete_input != "":
        if _p4_run_command(".", ["p4", "-x", "-", "-z", "tag", "revert"], delete_input) is None:
            return False
        if _p4_run_command(".", ["p4", "-x", "-", "-z", "tag", "delete", "-c", cl_number], delete_input) is None:
            return False

    reconcile_input = ""
    files = list(files)
    for file in files:
        reconcile_input += file
        if os.path.isdir(file):
            reconcile_input +=  "/..."
        reconcile_input += "\n"

    _p4_run_command(".", ["p4", "-x", "-", "-z", "tag", "reconcile", "-c", cl_number], reconcile_input, False)
    return True

#-------------------------------------------------------------------------------
def p4_get_changelist_description(cl_number):
    return _p4_parse_command_output(".", ["p4", "-z", "tag", "describe", cl_number], r"\.\.\. desc (.*)")

#-------------------------------------------------------------------------------
def p4_get_last_synced_changelist():
    workspace = p4_get_workspace()

    if workspace is None:
        return None

    cl_number = _p4_parse_command_output(".", ["p4", "-z", "tag", "changes", "-s", "submitted", "-m1", "@{0}".format(workspace)], r"\.\.\. change (\d+)")

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
    change_list_form = CREATE_CHANGELIST_FORM_TEMPLATE.format(user        = user,
                                                              workspace   = p4_get_workspace(),
                                                              description = description)

    return _p4_parse_command_output(".", ["p4", "-z", "tag","change", "-i"], r"Change (\d+) created\.", change_list_form)

#-------------------------------------------------------------------------------
def p4_get_pending_changelists():
    return _p4_parse_command_output_list(".", ["p4", "-z", "tag", "changes", "-c", p4_get_workspace(), "-s", "pending"], r"\.\.\. change (\d+)")

#-------------------------------------------------------------------------------
def p4_get_user():
    return _p4_parse_command_output(".", ["p4", "-z", "tag", "user", "-o"], r"^\.\.\. User (.*)$")

#-------------------------------------------------------------------------------
def p4_get_workspace():
    return _p4_parse_command_output(".", ["p4", "-z", "tag", "info"], r"^\.\.\. clientName (.*)$")

#-------------------------------------------------------------------------------
def p4_is_file_versioned(file_path):
    result, output, error = capture_process_output(".", ["p4", "-z", "tag", "fstat", file_path], None, 'cp437')
    # Il faut checker que le fichier a pas été ajouté puis delete
    if re.search(r"\.\.\.\s*headAction\s*delete", output) is not None:
        return False
    return not "no such file(s)" in error and not "file(s) not in client" in error

#-------------------------------------------------------------------------------
def p4_revert_changelist(cl_number):
    output = _p4_run_command(".", ["p4", "-z", "tag", "revert", "-c", cl_number, "//..."])
    return output is not None

#-------------------------------------------------------------------------------
def p4_revert_unchanged(cl_number):
    output = _p4_run_command(".", ["p4", "-z", "tag", "revert", "-a", "-c", cl_number, "//..."])
    return output is not None

#-------------------------------------------------------------------------------
def p4_submit(cl_number):
    log_notification("Submiting changelist {0}...", cl_number)
    result, output, error = capture_process_output(".", ["p4", "-z", "tag", "submit", "-f", "revertunchanged", "-c", cl_number], None, 'cp437')

    if error is not None and error != "":
        if "No files to submit." in error:
            log_notification("CL {0} is empty, deleting it...", cl_number)
            return p4_delete_changelist(cl_number)
        log_error("Perforce error submiting changelist {0} : {1}", cl_number, error)
        return False

    return True

#-------------------------------------------------------------------------------
def p4_sync(file = None, cl_number = None):
    p4_command = ["p4", "-z", "tag", "sync"]
    file_spec = ""

    if file is not None:
        file_spec = file

    if cl_number is not None:
        file_spec += "@%s" % cl_number

    if len(file_spec) > 0:
        p4_command += [file_spec]

    result, output, error = capture_process_output('.', p4_command, None, 'cp437')
    if (result != 0 or error != '') and 'file(s) up-to-date' not in error:
            log_error("Error syncing : {0}", error)
            return False

    return True

#---------------------------------------------------------------
def p4_get_modified_files(*cl_numbers):
    for cl_number in cl_numbers:
        actions = _p4_parse_command_output_list(".", ["p4", "-z", "tag", "describe", cl_number], r"^\.\.\. action[\w]*(.*)$")
        assets = _p4_parse_command_output_list(".", ["p4", "-z", "tag", "describe", cl_number], r"^\.\.\. depotFile[\w]*(.*)$")
        for i in range(0,len(assets)):
            assets[i] = _p4_parse_command_output(".", ["p4", "-z", "tag", "fstat", assets[i]], r"^\.\.\. clientFile(.*)$")
            if assets[i] != None:
                assets[i] = os.path.normpath(assets[i])
            else:
                assets[i] = ''
            yield (assets[i], actions[i])

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
        self._change_list_description = change_list_description
        self._success                 = True
        self._cl_number               = None
        self._submit_on_success       = submit_on_success
        self._revert_unchanged        = revert_unchanged
        self._add_not_versioned_files = add_not_versioned_files
        self._paths                   = []

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
            return True

        self._paths.append(path)
        if p4_is_file_versioned(path):
           if p4_edit(self._cl_number, path):
              return True
        elif not self._add_not_versioned_files:
            return True
        elif p4_add(self._cl_number, path):
             return True

        log_error("An error occurred while adding file to Perforce transaction")
        self._success = False

        return False

    #---------------------------------------------------------------------------
    def delete(self, path):
        return p4_delete(self._cl_number, path)

    #---------------------------------------------------------------------------
    def abort(self):
        self._success = False

    #---------------------------------------------------------------------------
    def __exit__(self, type, value, trace):
        if value is not None:
            raise value

        if not self._success and self._cl_number is not None:
            log_verbose("Perforce transaction aborted, reverting and deleting CLs…")
            p4_revert_changelist(self._cl_number)
            p4_delete_changelist(self._cl_number)
        elif self._cl_number is not None:
            if self._revert_unchanged:
                log_verbose("Reverting unchanged files…")
                if not p4_revert_unchanged(self._cl_number):
                    return False
            if self._submit_on_success:
                log_verbose("Committing result…")
                return p4_submit(self._cl_number)
        else:
            log_error("An error occurred while entering Perforce transaction, so not doing anything here.")
        return True

#-------------------------------------------------------------------------------
def _p4_run_command(directory, command, input = None, log_errors = True):
    result, output, error = capture_process_output(directory, command, input, 'cp437')
    if result != 0 or error != '':
        if log_errors:
            log_error("Perforce error: {1}", input, error.rstrip('\r\n'))
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
            log_error('Error while parsing p4 command "{0}" output (got {1})', " ".join(command), output)
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