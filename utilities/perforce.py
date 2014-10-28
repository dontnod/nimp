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
def run_perforce_command(directory, command, input = None):
    result, output, error = capture_process_output(".", command, input)
    if( result != 0):
        log_error("Error while running perforce command {0} : {1}", " ".join(command), error)
        return None

    return output

#-------------------------------------------------------------------------------
def run_silent_perforce_command(directory, command, input = None):
    result, output, error = capture_process_output(".", command, None)
    if( result != 0):
        return None

    return output

#-------------------------------------------------------------------------------
def parse_perforce_command_output(directory, command, pattern, input = None):
    output = run_perforce_command(directory, command, input)

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
def parse_perforce_command_output_silent(directory, command, pattern, input = None):
    output = run_perforce_command(directory, command, input)

    if output is None:
        return None

    match = re.search(pattern, output, re.MULTILINE)

    if(match is None):
        return None

    result = match.group(1)
    result = result.strip()
    return result

#-------------------------------------------------------------------------------
def get_perforce_user():
    return parse_perforce_command_output(".", ["p4", "-z", "tag", "user", "-o"], "^\.\.\. User (.*)$")

#-------------------------------------------------------------------------------
def list_perforce_clients():
    perforce_user = get_perforce_user()
    result        = []

    if perforce_user is None:
        return None

    output = run_perforce_command(".", ["p4", "-z", "tag", "clients", "-u", perforce_user])

    if( output is None):
        return None

    client_matches = re.finditer("\.\.\. client (.*)", output)

    for client_match in client_matches:
         result = result + [client_match.group(1).strip()]

    return result

#-------------------------------------------------------------------------------
def get_perforce_client_infos(client_name):
    result        = {}

    if perforce_user is None:
        return None

    output = run_perforce_command(".", ["p4", "-z", "tag", "client", "-o", client_name])

    if( output is None):
        return None

    root_match = re.finditer("\.\.\. root (.*)", output)

    if(root_match is None):
        log_error("Unable to parse perforce output.")
        return None

    result["root"] = root_match.group(1)

#------------------------------------------------------------------------------
def get_perforce_workspaces_containing_file(workspace_path):
    result        = []

    clients = list_perforce_clients()

    for client in clients:
        output = run_silent_perforce_command(".", ["p4", "-z", "tag", "-c", client, "where", workspace_path])

        if(output is None):
            continue

        if(output != ''):
            result = result + [client]
    return result

#-------------------------------------------------------------------------------
def is_file_source_controled(workspace, file_path):
    result, output, error = capture_process_output(".", ["p4", "-z", "tag", "-c", workspace, "fstat", file_path])
    return not "no such file(s)" in error

#-------------------------------------------------------------------------------
def get_perforce_disk_file_path(workspace_path, client_name = None):
    result = {}

    if(client_name is None):
        workspaces = get_perforce_workspaces_containing_file(workspace_path)
        if workspaces is None:
           return None
        if len(workspaces) == 0:
            log_error("Unable to find a workspace containing file {0}", workspace_path)
            return None
        for candidate_client_name in workspaces:
            result = get_perforce_disk_file_path(workspace_path, candidate_client_name)
            if os.path.exists(result):
                return result
        return None

    return parse_perforce_command_output(".", ["p4", "-z", "tag", "-c", client_name, "where", workspace_path], "\.\.\. path (.*)")

#-------------------------------------------------------------------------------
def create_perforce_changelist(workspace, description):
    user             = get_perforce_user()
    change_list_form = CREATE_CHANGELIST_FORM_TEMPLATE.format(user          = user,
                                                              workspace     = workspace,
                                                              description   = description)

    return parse_perforce_command_output(".", ["p4", "-z", "tag", "change", "-i"], "Change ([0-9]*) created\.", change_list_form)

#-------------------------------------------------------------------------------
def edit_file(workspace, cl_number, file):
    output = run_perforce_command(".", ["p4", "-z", "tag", "-c", workspace, "edit", "-c", cl_number, file])

    if(output is None):
        return False

    return True

#-------------------------------------------------------------------------------
def add_file(workspace, cl_number, file):
    output = run_perforce_command(".", ["p4", "-z", "tag", "-c", workspace, "add", "-c", cl_number, file])

    if(output is None):
        return False

    return True

#-------------------------------------------------------------------------------
def revert_changelist(workspace, cl_number):
    output = run_perforce_command(".", ["p4", "-z", "tag", "-c", workspace, "revert", "-c", cl_number])

    if(output is None):
        return False

    return True

#-------------------------------------------------------------------------------
class PerforceTransaction:
    def __init__(self, workspace, change_list_description, file_list):
        self._workspace                 = workspace
        self._change_list_description   = change_list_description
        self._file_list                 = file_list
        self._success                   = True
        self._cl_number                 = None

    def __enter__(self):
        self._cl_number = create_perforce_changelist(self._workspace, self._change_list_description)

        if self._cl_number is None:
            self._success = False
            raise Exception()

        for file_it in self._file_list:
            if is_file_source_controled(self._workspace, file_it):
                if not edit_file(self._workspace, self._cl_number, file_it):
                    self._success = False
                    raise Exception()

        return self

    def abort(self):
        self._success = False

    def __exit__(self, type, value, trace):
        if self._success and self._cl_number is not None:
            for file_it in self._file_list:
                if not is_file_source_controled(self._workspace, file_it):
                    if not add_file(self._workspace, self._cl_number, file_it):
                        self._success = False
                        break

        if not self._success and self._cl_number is not None:
            revert_changelist(self._workspace, self._cl_number)

        return True

