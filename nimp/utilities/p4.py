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
''' Utilities related to compilation '''

import logging
import os
import os.path
import re

import nimp.utilities.system

_CREATE_CHANGELIST_FORM_TEMPLATE = "\
Change: new\n\
User:   {user}\n\
Client: {workspace}\n\
Status: pending\n\
Description:\n\
        {description}"

def add(cl_number, path):
    ''' Adds a file to source control '''
    output = _run_command(".", ["p4", "-z", "tag", "add", "-c", cl_number, path])
    return output is not None

def clean_workspace():
    ''' Revert and deletes all pending changelists in current workspace '''
    result = True
    _run_command(".", ["p4", "-z", "tag", "revert", "//..."])
    pending_changelists = get_pending_changelists()

    for cl_number in pending_changelists:
        logging.info("Deleting changelist %s", cl_number)
        result = result and delete_changelist(cl_number)

    return result

def delete(cl_number, path):
    ''' Deletes given file in given changelist '''
    output = _run_command(".", ["p4", "-z", "tag", "delete", "-c", cl_number, path])
    return output is not None

def delete_changelist(cl_number):
    ''' Deletes a changelist from client '''
    output = _run_command(".", ["p4", "-z", "tag", "change", "-d", cl_number])
    return output is not None

def get_files_status(*files):
    ''' Returns a tuple containing file name, head action and local action for
        all files given '''
    files = list(files)
    for i in range(0, len(files)):
        if os.path.isdir(files[i]):
            files[i] = files[i] + "/..."

    _, output, _ = nimp.utilities.system.capture_process_output(".", ["p4", "-x", "-", "-z", "tag","fstat"], '\n'.join(files), 'cp437')
    files_infos = output.strip().replace('\r', '').split('\n\n')

    for file_info in files_infos:
        if "no such file(s)" in file_info or "file(s) not in client" in file_info:
            continue
        file_name_match   = re.search(r"\.\.\.\s*clientFile\s*(.*)", file_info)
        head_action_match = re.search(r"\.\.\.\s*headAction\s*(\w*)", file_info)
        action_match      = re.search(r"\.\.\.\s*action\s*(\w*)", file_info)

        if file_name_match is None:
            logging.error("Got unexpected output from p4 fstat : %s", file_info)
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

def edit(cl_number, *files):
    ''' Open given file for input in given changelist '''
    edit_input = ""

    for file_name, head_action, _ in get_files_status(*files):
        if head_action == "delete":
            logging.debug("Ignoring deleted file %s", file_name)
            continue
        logging.debug("Adding file %s to checkout", file_name)
        edit_input += file_name + "\n"

    output = _run_command(".", ["p4", "-x", "-", "-z", "tag", "edit", "-c", cl_number], edit_input)
    return output is not None

def reconcile(cl_number, *files):
    ''' Reconciles given files in given cls '''
    delete_input = ""
    for file_name, _, action in get_files_status(*files):
        if action == "edit" and not os.path.exists(file_name):
            logging.debug("Manually reverting and deleting checkouted and missing file %s", file_name)
            delete_input += file_name + "\n"

    if delete_input != "":
        if _run_command(".", ["p4", "-x", "-", "-z", "tag", "revert"], delete_input) is None:
            return False
        if _run_command(".", ["p4", "-x", "-", "-z", "tag", "delete", "-c", cl_number], delete_input) is None:
            return False

    reconcile_input = ""
    files = list(files)
    for file in files:
        reconcile_input += file
        if os.path.isdir(file):
            reconcile_input +=  "/..."
        reconcile_input += "\n"

    _run_command(".", ["p4", "-x", "-", "-z", "tag", "reconcile", "-c", cl_number], reconcile_input, False)
    return True

def get_changelist_description(cl_number):
    ''' Returns description of given changelist '''
    return _parse_command_output(".", ["p4", "-z", "tag", "describe", cl_number], r"\.\.\. desc (.*)")

def get_last_synced_changelist():
    ''' Returns the last synced changelist '''
    workspace = get_workspace()

    if workspace is None:
        return None

    cl_number = _parse_command_output(".", ["p4", "-z", "tag", "changes", "-s", "submitted", "-m1", "@{0}".format(workspace)], r"\.\.\. change (\d+)")

    if cl_number is None:
        return None

    return cl_number

def get_or_create_changelist(description):
    ''' Creates or returns changelist number if it's not already created '''
    pending_changelists = get_pending_changelists()

    for cl_number in pending_changelists:
        pending_cl_desc = get_changelist_description(cl_number)

        if pending_cl_desc is None:
            return None

        if description.lower() == pending_cl_desc.lower():
            return cl_number

    user = get_user()
    change_list_form = _CREATE_CHANGELIST_FORM_TEMPLATE.format(user        = user,
                                                               workspace   = get_workspace(),
                                                               description = description)

    return _parse_command_output(".", ["p4", "-z", "tag","change", "-i"], r"Change (\d+) created\.", change_list_form)

def get_pending_changelists():
    ''' Returns pending changelists '''
    return _parse_command_output_list(".", ["p4", "-z", "tag", "changes", "-c", get_workspace(), "-s", "pending"], r"\.\.\. change (\d+)")

def get_user():
    ''' Returns current perforce user '''
    return _parse_command_output(".", ["p4", "-z", "tag", "user", "-o"], r"^\.\.\. User (.*)$")

def get_workspace():
    ''' Returns current workspace '''
    return _parse_command_output(".", ["p4", "-z", "tag", "info"], r"^\.\.\. clientName (.*)$")

def is_file_versioned(file_path):
    ''' Checks if a file is known by the source control '''
    _, output, error = nimp.utilities.system.capture_process_output(".", ["p4", "-z", "tag", "fstat", file_path], None, 'cp437')
    # Checks if the file was not added then deleted
    if re.search(r"\.\.\.\s*headAction\s*delete", output) is not None:
        return False
    return "no such file(s)" not in error and "file(s) not in client" not in error

def revert_changelist(cl_number):
    ''' Reverts given changelist '''
    output = _run_command(".", ["p4", "-z", "tag", "revert", "-c", cl_number, "//..."])
    return output is not None

def revert_unchanged(cl_number):
    ''' Reverts unchanged files in given changelist '''
    output = _run_command(".", ["p4", "-z", "tag", "revert", "-a", "-c", cl_number, "//..."])
    return output is not None

def submit(cl_number):
    ''' Submits given changelist '''
    logging.info("Submiting changelist %s...", cl_number)
    _, _, error = nimp.utilities.system.capture_process_output(".", ["p4", "-z", "tag", "submit", "-f", "revertunchanged", "-c", cl_number], None, 'cp437')

    if error is not None and error != "":
        if "No files to submit." in error:
            logging.info("CL %s is empty, deleting it...", cl_number)
            return delete_changelist(cl_number)
        logging.error("Perforce error submiting changelist %s : %s", cl_number, error)
        return False

    return True

def sync(file = None, cl_number = None):
    ''' Udpate given file '''
    command = ["p4", "-z", "tag", "sync"]
    file_spec = ""

    if file is not None:
        file_spec = file

    if cl_number is not None:
        file_spec += "@%s" % cl_number

    if len(file_spec) > 0:
        command += [file_spec]

    result, _, error = nimp.utilities.system.capture_process_output('.', command, None, 'cp437')
    if (result != 0 or error != '') and 'file(s) up-to-date' not in error:
        logging.error("Error syncing : %s", error)
        return False

    return True

def get_modified_files(*cl_numbers, root = '//...'):
    ''' Returns files modified by given changelists '''
    for cl_number in cl_numbers:
        outputs = _parse_command_output_patterns(".", ["p4", "-z", "tag", "fstat", "-e", cl_number ,root], r"^\.\.\. depotFile(.*)$", r"^\.\.\. headAction(.*)")

        #outputs length must be 2 because we must only have the clientFile and the headAction in this list
        if outputs is not None and len(outputs) == 2:
            assets = outputs[0]
            actions = outputs[1]
            for i in range(0,len(assets)):
                if assets[i] != None:
                    assets[i] = os.path.normpath(assets[i])
                else:
                    assets[i] = ''
                yield (assets[i], actions[i])
        else:
            if outputs is None:
                logging.warning('Error when executing command fstat -e on Changelist ' + str(cl_number) + '. Please check that the changelist exists or that you are in the good working directory.')
            yield ('', '')

def _run_command(directory, command, stdin = None, log_errors = True):
    result, output, error = nimp.utilities.system.capture_process_output(directory, command, stdin, 'cp437')
    if result != 0 or error != '':
        if log_errors:
            logging.error("Perforce error: %s", error.rstrip('\r\n'))
        return None
    return output

def _parse_command_output(directory, command, pattern, stdin = None, log_errors = True):
    output = _run_command(directory, command, stdin, log_errors)

    if output is None:
        return None

    match = re.search(pattern, output, re.MULTILINE)

    if match is None:
        if log_errors:
            logging.error('Error while parsing p4 command "%s" output (got %s)', " ".join(command), output)
        return None

    result = match.group(1)
    result = result.strip()
    return result

def _parse_command_output_list(directory, command, pattern, stdin = None, log_errors = True):
    output = _run_command(directory, command, stdin, log_errors)

    if output is None:
        return None

    matches = list(re.finditer(pattern, output, re.MULTILINE))

    result = []
    for match in matches:
        match_string = match.group(1)
        match_string = match_string.strip()
        result.append(match_string)
    return result

def _parse_command_output_patterns(directory, command, *patterns, stdin = None, log_errors = True):
    output = _run_command(directory, command, stdin, log_errors)

    if output is None:
        return None

    outputs = []

    for pattern in patterns:
        matches = list(re.finditer(pattern, output, re.MULTILINE))
        result = []
        for match in matches:
            match_string = match.group(1)
            match_string = match_string.strip()
            result.append(match_string)
        outputs.append(result)

    return outputs
