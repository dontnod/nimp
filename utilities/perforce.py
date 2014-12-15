# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
import os
import re
import subprocess
import sys
import threading
import time
import tempfile

from utilities.processes import *
from utilities.paths     import *


CREATE_CHANGELIST_FORM_TEMPLATE = "\
Change: new\n\
Client: {workspace}\n\
User:   {user}\n\
Status: pending\n\
Description:\n\
        {description}"

#-------------------------------------------------------------------------------
def p4_add(workspace, cl_number, path, pattern = '*'):
    files = get_matching_files(path, pattern)

    if files is None:
        return False

    for file in files:
        log_verbose("Adding {0} to perforce")
        if _p4_run_command(".", ["p4", "-z", "tag", "-c", workspace, "add", "-c", cl_number, file]) is None:
            return False

    return True

#-------------------------------------------------------------------------------
def p4_clean_workspace(workspace = None):
    workspace = workspace or p4_get_first_workspace_containing_path(".")

    if workspace is None:
        return False

    log_notification("Reverting all opened files in workspace {0}", workspace)
    result = _p4_run_command(".", ["p4", "-c", workspace, "-z", "tag", "revert", "//..."]) is not None

    pending_changelists = p4_get_pending_changelists(workspace)

    for cl_number in pending_changelists:
        log_notification("Deleting changelist {0}", cl_number)
        result = result and p4_delete_changelist(cl_number)

    return result

#-------------------------------------------------------------------------------
def p4_delete_changelist(cl_number):
    workspace = p4_get_changelist_workspace(cl_number)
    output = _p4_run_command(".", ["p4", "-z", "tag", "-c", workspace, "change", "-d", cl_number])
    return output is not None

#-------------------------------------------------------------------------------
def p4_edit(workspace, cl_number, path, pattern = '*'):
    files = get_matching_files(path, pattern)

    if files is None:
        return False

    for file in files:
        if _p4_run_command(".", ["p4", "-z", "tag", "-c", workspace, "edit", "-c", cl_number, file]) is None:
            return False

    return True

#-------------------------------------------------------------------------------
def p4_get_changelist_description(cl_number):
    return _p4_parse_command_output(".", ["p4", "-z", "tag", "describe", cl_number], "\.\.\. desc (.*)")

#-------------------------------------------------------------------------------
def p4_get_changelist_workspace(cl_number):
    return _p4_parse_command_output(".", ["p4", "-z", "tag", "describe", cl_number], "\.\.\. client (.*)")

#-------------------------------------------------------------------------------
def p4_get_disk_path(workspace_path, client_name = None):
    result = {}

    if(client_name is None):
        workspaces = p4_get_workspaces_containing_path(workspace_path)
        if workspaces is None:
           return None
        if len(workspaces) == 0:
            log_error("Unable to find a workspace containing file {0}", workspace_path)
            return None
        for candidate_client_name in workspaces:
            result = p4_get_disk_path(workspace_path, candidate_client_name)
            if os.path.exists(result):
                return result
        return None

    return _p4_parse_command_output(".", ["p4", "-z", "tag", "-c", client_name, "where", workspace_path], "\.\.\. path (.*)")

#------------------------------------------------------------------------------
def p4_get_first_workspace_containing_path(disk_path):
    log_verbose('Finding workspace mapped to {0}', disk_path)
    workspaces = p4_get_workspaces_containing_path(disk_path)
    if workspaces is None:
        log_error("Unable to find a workspace containing file {0}", disk_path)
        return None
    if len(workspaces) == 0:
        log_error("Unable to find a workspace containing file {0}", disk_path)
        return None
    log_verbose('Found workspace {0}', workspaces[0])
    return workspaces[0]

#-------------------------------------------------------------------------------
def p4_get_last_synced_changelist(workspace = None):
    workspace = workspace or p4_get_first_workspace_containing_path(".")

    if workspace is None:
        return None

    cl_number = _p4_parse_command_output(".", ["p4", "-z", "tag", "changes", "-s", "submitted", "-m1", "@{0}".format(workspace)], "\.\.\. change ([0-9]*)")

    if(cl_number is None):
        return None

    return cl_number

#-------------------------------------------------------------------------------
def p4_get_or_create_changelist(workspace, description):

    pending_changelists = p4_get_pending_changelists(workspace)

    for cl_number in pending_changelists:
        pending_cl_desc = p4_get_changelist_description(cl_number)

        if pending_cl_desc is None:
            return None

        if description.lower() == pending_cl_desc.lower():
            return cl_number

    user             = p4_get_user()
    change_list_form = CREATE_CHANGELIST_FORM_TEMPLATE.format(user          = user,
                                                              workspace     = workspace,
                                                              description   = description)

    return _p4_parse_command_output(".", ["p4", "-z", "tag", "-c", workspace, "change", "-i"], "Change ([0-9]*) created\.", change_list_form)

#-------------------------------------------------------------------------------
def p4_get_pending_changelists(workspace = None):
    workspace = workspace or p4_get_first_workspace_containing_path(".")

    if workspace is None:
        return None

    return _p4_parse_command_output_list(".", ["p4", "-z", "tag", "changes", "-c", workspace, "-s", "pending"], "\.\.\. change ([0-9]*)")

#-------------------------------------------------------------------------------
def p4_get_user():
    return _p4_parse_command_output(".", ["p4", "-z", "tag", "user", "-o"], "^\.\.\. User (.*)$")

#------------------------------------------------------------------------------
def p4_get_workspaces_containing_path(workspace_path):
    result        = []

    workspaces = p4_list_workspaces()

    for client in workspaces:
        # FIX ME : Peut être trouver une commande qui ne renvoie pas d'erreur si un fichier n'est pas versionné
        if os.path.isdir(workspace_path):
            workspace_path += "/..."
        output = _p4_run_command(".", ["p4", "-z", "tag", "-c", client, "where", workspace_path], log_errors = False)

        if(output is None):
            continue

        if(output != ''):
            result = result + [client]
    return result

#-------------------------------------------------------------------------------
def p4_is_file_versioned(workspace, file_path):
    result, output, error = capture_process_output(".", ["p4", "-z", "tag", "-c", workspace, "fstat", file_path])
    return not "no such file(s)" in error

#-------------------------------------------------------------------------------
def p4_list_workspaces():
    perforce_user = p4_get_user()
    result        = []

    if perforce_user is None:
        return None

    output = _p4_run_command(".", ["p4", "-z", "tag", "clients", "-u", perforce_user])

    if( output is None):
        return None

    client_matches = re.finditer("\.\.\. client (.*)", output)

    for client_match in client_matches:
        result = result + [client_match.group(1).strip()]

    return result

#-------------------------------------------------------------------------------
def p4_reconcile(workspace, cl_number, path):
    if os.path.isdir(path):
        path = path + "/..."

    if _p4_run_command(".", ["p4", "-z", "tag", "-c", workspace, "reconcile", "-c", cl_number, path]) is None:
            return False
    return True

#-------------------------------------------------------------------------------
def p4_revert_changelist(cl_number):
    workspace = p4_get_changelist_workspace(cl_number) # Youpi perforce tu peux pas te démerder tout seul

    if workspace is None:
        return False

    return _p4_run_command(".", ["p4", "-z", "tag", "-c", workspace, "revert", "-c", cl_number, "//..."]) is not None

#-------------------------------------------------------------------------------
def p4_revert_unchanged(cl_number):
    workspace = p4_get_changelist_workspace(cl_number) # Youpi perforce tu peux pas te démerder tout seul

    if workspace is None:
        return False

    return _p4_run_command(".", ["p4", "-z", "tag", "-c", workspace, "revert", "-a", "-c", cl_number, "//..."]) is not None

#-------------------------------------------------------------------------------
def p4_submit(cl_number):
    p4_command = ["p4", "-z", "tag", "-c", workspace, "submit", "-f", "revertunchanged", "-c", cl_number]
    return _p4_run_command(".", p4_command) is not None

#-------------------------------------------------------------------------------
def p4_sync(workspace, cl_number = None):
    p4_command = ["p4", "-z", "tag", "-c", workspace, "sync"]

    if cl_number is not None:
        p4_command = p4_command + ["@{0}".format(cl_number)]

    return _p4_run_command(".", p4_command) is not None

#-------------------------------------------------------------------------------
class PerforceTransaction:
    #---------------------------------------------------------------------------
    def __init__(self, change_list_description, *paths, submit_on_success = False, workspace = None):
        self._workspace                 = workspace or p4_get_first_workspace_containing_path(".")
        self._change_list_description   = change_list_description
        self._paths                     = list(paths)
        self._success                   = True
        self._cl_number                 = None
        self._submit_on_success         = submit_on_success

    #---------------------------------------------------------------------------
    def __enter__(self):
        self._cl_number = p4_get_or_create_changelist(self._workspace, self._change_list_description)

        if self._cl_number is None:
            self._success = False
            raise Exception()

        for path in self._paths:
            if not p4_edit(self._workspace, self._cl_number, path):
                self._success = False

        return self

    #---------------------------------------------------------------------------
    def add(self, path):
        self._paths.append(path)
        if not p4_edit(self._workspace, self._cl_number, path):
            self._success = False

    #---------------------------------------------------------------------------
    def abort(self):
        self._success = False

    #---------------------------------------------------------------------------
    def __exit__(self, type, value, trace):
        if value is not None:
            raise value

        for path in self._paths:
            if not p4_reconcile(self._workspace, self._cl_number, path):
                self._success = False
                break

        if not self._success and self._cl_number is not None:
            p4_revert_changelist(self._cl_number)
            p4_delete_changelist(self._cl_number)
        elif self._success and self._submit_on_success:
            return p4_submit(self._cl_number)
        elif self._success:
            return p4_revert_unchanged(self._cl_number)
        return True

#-------------------------------------------------------------------------------
def _p4_run_command(directory, command, input = None, log_errors = True):
    result, output, error = capture_process_output(directory, command, input)
    if( result != 0):
        if log_errors:
            log_error("Error while running perforce command {0} : {1}", " ".join(command), error)
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
