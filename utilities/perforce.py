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


CREATE_CHANGELIST_FORM_TEMPLATE = "\
Change: new\n\
Client: {workspace}\n\
User:   {user}\n\
Status: pending\n\
Description:\n\
        {description}"

#-------------------------------------------------------------------------------
def p4_run_command(directory, command, input = None):
    result, output, error = capture_process_output(directory, command, input)
    if( result != 0):
        log_error("Error while running perforce command {0} : {1}", " ".join(command), error)
        return None

    return output

#-------------------------------------------------------------------------------
def p4_run_command_silent(directory, command, input = None):
    result, output, error = capture_process_output(directory, command, None)
    if( result != 0):
        return None

    return output

#-------------------------------------------------------------------------------
def p4_parse_command_output(directory, command, pattern, input = None):
    output = p4_run_command(directory, command, input)

    if output is None:
        return None

    match = re.search(pattern, output, re.MULTILINE)

    if(match is None):
        log_error("Error while parsing p4 command \'{0}\' output (got {1})", " ".join(command), output)
        return None

    result = match.group(1)
    result = result.strip()
    return result

#-------------------------------------------------------------------------------
def p4_parse_command_output_silent(directory, command, pattern, input = None):
    output = p4_run_command(directory, command, input)

    if output is None:
        return None

    match = re.search(pattern, output, re.MULTILINE)

    if(match is None):
        return None

    result = match.group(1)
    result = result.strip()
    return result

#-------------------------------------------------------------------------------
def p4_get_user():
    return p4_parse_command_output(".", ["p4", "-z", "tag", "user", "-o"], "^\.\.\. User (.*)$")

#-------------------------------------------------------------------------------
def p4_list_workspaces():
    perforce_user = p4_get_user()
    result        = []

    if perforce_user is None:
        return None

    output = p4_run_command(".", ["p4", "-z", "tag", "clients", "-u", perforce_user])

    if( output is None):
        return None

    client_matches = re.finditer("\.\.\. client (.*)", output)

    for client_match in client_matches:
         result = result + [client_match.group(1).strip()]

    return result

#-------------------------------------------------------------------------------
def p4_sync(workspace, cl_number = None):
    p4_command = ["p4", "-z", "tag", "-c", workspace, "sync"]

    if cl_number is not None:
        p4_command = p4_command + ["@{0}".format(cl_number)]


    output = p4_run_command(".", p4_command)

    if( output is None):
        return False

    return True

#------------------------------------------------------------------------------
def p4_get_workspaces_containing_path(workspace_path):
    result        = []

    workspaces = p4_list_workspaces()

    for client in workspaces:
        # FIX ME : Peut être trouver une commande qui ne renvoie pas d'erreur si un fichier n'est pas versionné
        if os.path.isdir(workspace_path):
            workspace_path += "/..."
        output = p4_run_command_silent(".", ["p4", "-z", "tag", "-c", client, "where", workspace_path])

        if(output is None):
            continue

        if(output != ''):
            result = result + [client]
    return result

#-------------------------------------------------------------------------------
def p4_is_file_versionned(workspace, file_path):
    result, output, error = capture_process_output(".", ["p4", "-z", "tag", "-c", workspace, "fstat", file_path])
    return not "no such file(s)" in error

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

    return p4_parse_command_output(".", ["p4", "-z", "tag", "-c", client_name, "where", workspace_path], "\.\.\. path (.*)")

#-------------------------------------------------------------------------------
def p4_create_changelist(workspace, description):
    user             = p4_get_user()
    change_list_form = CREATE_CHANGELIST_FORM_TEMPLATE.format(user          = user,
                                                              workspace     = workspace,
                                                              description   = description)

    return p4_parse_command_output(".", ["p4", "-z", "tag", "change", "-i"], "Change ([0-9]*) created\.", change_list_form)

#-------------------------------------------------------------------------------
def p4_edit(workspace, cl_number, file):
    output = p4_run_command(".", ["p4", "-z", "tag", "-c", workspace, "edit", "-c", cl_number, file])

    if(output is None):
        return False

    return True

#-------------------------------------------------------------------------------
def p4_edit_in_changelist(changelist_description, file):
    workspaces = p4_get_workspaces_containing_path(file)

    if workspaces is None or len(workspaces) == 0:
        return None

    workspace = workspaces[0]
    cl_number = p4_create_changelist(workspace, changelist_description)

    if cl_number is None:
        return None

    if not p4_edit(workspace, cl_number, file):
        p4_revert_changelist(cl_number)
        return False

    return cl_number

#-------------------------------------------------------------------------------
def p4_add(workspace, cl_number, file):
    output = p4_run_command(".", ["p4", "-z", "tag", "-c", workspace, "add", "-c", cl_number, file])

    if(output is None):
        return False

    return True

#-------------------------------------------------------------------------------
def p4_revert_changelist(cl_number):
    output = p4_run_command(".", ["p4", "-z", "tag", "revert", "-c", cl_number])

    if(output is None):
        return False

    return True

#-------------------------------------------------------------------------------
def p4_get_last_synced_changelist(workspace):
    cl_number = p4_parse_command_output(".", ["p4", "-z", "tag", "changes", "-s", "submitted", "-m1", "@{0}".format(workspace)], "\.\.\. change ([0-9]*)")

    if(cl_number is None):
        return None

    return cl_number

#-------------------------------------------------------------------------------
class PerforceTransaction:
    def __init__(self, workspace, change_list_description, file_list = []):
        self._workspace                 = workspace
        self._change_list_description   = change_list_description
        self._file_list                 = file_list
        self._success                   = True
        self._cl_number                 = None

    def __enter__(self):
        self._cl_number = p4_create_changelist(self._workspace, self._change_list_description)

        if self._cl_number is None:
            self._success = False
            raise Exception()

        for file_it in self._file_list:
            self.add_file(file_it)

        return self

    def add_file(self, file_name):
        self._file_list = self._file_list + [file_name]
        if p4_is_file_versionned(self._workspace, file_name):
            if not p4_edit(self._workspace, self._cl_number, file_name):
                self._success = False

    def abort(self):
        self._success = False

    def __exit__(self, type, value, trace):
        if value is not None:
            raise value
        if self._success and self._cl_number is not None:
            for file_it in self._file_list:
                if not p4_is_file_versionned(self._workspace, file_it):
                    if not p4_add(self._workspace, self._cl_number, file_it):
                        self._success = False
                        break

        if not self._success and self._cl_number is not None:
            p4_revert_changelist(self._cl_number)

        return True

