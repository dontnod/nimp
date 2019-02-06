# -*- coding: utf-8 -*-
# Copyright © 2014—2017 Dontnod Entertainment

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

''' Perforce utilities '''

import argparse
import logging
import os
import os.path
import re

import nimp.sys.process
import nimp.system

_CREATE_CHANGELIST_FORM_TEMPLATE = "\
Change: new\n\
User:   {user}\n\
Client: {workspace}\n\
Status: pending\n\
Description:\n\
        {description}"

def add_arguments(parser):
    ''' Adds p4port, p4user, p4pass and p4client arguments to a command argument
        parser. Then you can Use :func:`nimp.utils.p4.sanitize` in your
        :func:`Command.sanitize` override to report Perforce misconfiguration. '''
    assert isinstance(parser, argparse.ArgumentParser)
    parser.add_argument('--p4port',
                        help = 'Perforce port',
                        type = str)

    parser.add_argument('--p4user',
                        help = 'Perforce user',
                        type = str)

    parser.add_argument('--p4pass',
                        help = 'Perforce pass',
                        type = str)

    parser.add_argument('--p4client',
                        help = 'Perforce workspace',
                        type = str)

def check_for_p4(env):
    ''' Checks for perforce availability.
        This will print an error message if perforce can't be used. '''
    p4 = get_client(env)
    if p4.get_workspace() is None:
        logging.error(('An error occured while checking Perforce availability. '
                       'Please check that p4 is in your path, and either you '
                       'specified correct p4port, p4client, p4user and p4pass '
                       'on the command line, either your p4 environment '
                       'settings are correctily set'))
        return False
    return True


def get_client(env):
    ''' Returns a p4 client initialized with parameters from the environment.
        Use the :func:`nimp.utils.p4.add_arguments` method to add needed
        arguments to a command sub-parser '''
    assert isinstance(env, nimp.environment.Environment)
    port   = env.p4port   if hasattr(env, 'p4port') else None
    user   = env.p4user   if hasattr(env, 'p4user') else None
    pwd    = env.p4pass   if hasattr(env, 'p4pass') else None
    client = env.p4client if hasattr(env, 'p4client') else None
    return P4(port, user, pwd, client)

class P4:
    ''' P4 Client '''
    #pylint: disable=too-many-public-methods

    def __init__(self, port = None, user = None, password = None, client = None):
        self._port = port
        self._user = user
        self._password = password
        self._client = client

    def add(self, cl_number, path):
        ''' Adds a file to source control '''
        assert isinstance(cl_number, str)
        assert isinstance(path, str)
        # Use -f to allow filenames with # * @ % characters
        output = self._run('add', '-f', '-c', cl_number, self._escape_filename(path))
        return output is not None

    def clean_workspace(self):
        ''' Revert and deletes all pending changelists in current workspace '''
        result = True
        self._run("revert", "//...")
        pending_changelists = self.get_pending_changelists()

        for cl_number in pending_changelists:
            assert isinstance(cl_number, str)
            logging.info("Deleting changelist %s", cl_number)
            result = result and self.delete_changelist(cl_number)

        return result

    def delete(self, cl_number, path):
        ''' Deletes given file in given changelist '''
        assert isinstance(cl_number, str)
        output = self._run("delete", "-c", cl_number, path)
        return output is not None

    def delete_changelist(self, cl_number):
        ''' Deletes a changelist from client '''
        output = self._run("change", "-d", cl_number)
        return output is not None

    def get_files_status(self, *files):
        ''' Returns a tuple containing file name, head action and local action for
            all files given '''
        files = [self._escape_filename(x) for x in files]
        for i, filename in enumerate(files):
            if os.path.isdir(filename):
                files[i] = filename + '/...'

        command = self._get_p4_command('-x', '-', 'fstat')
        _, output, error = nimp.sys.process.call(command, stdin='\n'.join(files), capture_output=True)
        files_infos = (output .strip()+ '\n\n' + error.strip()).strip().replace('\r', '').split('\n\n')

        for file_info in files_infos:
            file_info = file_info.strip()

            if file_info == '':
                continue

            if "no such file(s)" in file_info or "file(s) not in client" in file_info:
                continue

            if 'is not under client\'s root' in file_info:
                continue

            file_name_match   = re.search(r"\.\.\.\s*clientFile\s*(.*)", file_info)
            head_action_match = re.search(r"\.\.\.\s*headAction\s*(\w*)", file_info)
            action_match      = re.search(r"\.\.\.\s*action\s*(\w*)", file_info)

            assert file_name_match is not None

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

    def edit(self, cl_number, *files):
        ''' Open given file for input in given changelist '''
        files_to_edit = []
        for file_name, head_action, _ in self.get_files_status(*files):
            if head_action == "delete":
                logging.debug("Ignoring deleted file %s", file_name)
                continue
            logging.debug("Adding file %s to checkout", file_name)
            files_to_edit.append(self._escape_filename(file_name))

        edit_input = '\n'.join(files_to_edit)
        output = self._run('-x', '-', "edit", "-c",
                           cl_number, stdin=edit_input)
        return output is not None

    def reconcile(self, cl_number, *files):
        ''' Reconciles given files in given cl '''

        files = [self._escape_filename(x) for x in files]
        ret = True

        # List all currently edited depot files in our changelist
        edited_files = []
        for depot_file, action in self._parse_command_output(['describe', cl_number],
                                                             r'^\.\.\. depotFile\d* (.*)$',
                                                             r'^\.\.\. action\d* (.*)$'):
            if action == 'edit':
                edited_files.append(depot_file)

        # Find edited files that no longer exist on the filesystem
        files_to_delete = []
        for depot_file, path in self._parse_command_output(['-x', '-', 'where'],
                                                           r'^\.\.\. depotFile\d* (.*)$',
                                                           r'^\.\.\. path\d* (.*)$',
                                                           stdin='\n'.join(edited_files)):
            if not os.path.exists(path):
                logging.debug('Manually reverting and deleting checked out and missing file %s', path)
                files_to_delete.append(path)

        # Revert files that no longer belong here and mark them for delete
        delete_input = '\n'.join(files_to_delete)
        if self._run('-x', '-', 'revert', stdin=delete_input) is None:
            ret = False
        if self._run('-x', '-', 'delete', '-c', cl_number, stdin=delete_input) is None:
            ret = False

        # Revert unchanged files
        if self._run('revert', '-a', '-c', cl_number) is None:
            ret = False

        # Reconcile files with -a: add missing files to checkout if necessary
        #                  and -f: allow usage of # @ % * characters
        if self._run('-x', '-', 'reconcile', '-f', '-a', '-c', cl_number, stdin='\n'.join(files)) is None:
            ret = False

        return ret

    def get_current_changelist(self, path):
        ''' Returns the current changelist for the workspace '''
        perforce_path = (nimp.system.sanitize_path(path) + '/...') if path else '...'
        cl_number, = next(self._parse_command_output(['changes', '--max', '1', perforce_path + '#have'], r'\.\.\. change (\d+)'))
        return cl_number

    def get_changelists(self, *args):
        ''' Returns the current changelist for the workspace '''
        for cl_number, in self._parse_command_output(['changes'] + list(args), r'\.\.\. change (\d+)'):
            yield cl_number

    def get_last_synced_changelist(self):
        ''' Returns the last synced changelist '''
        cl_number, = next(self._parse_command_output(['changes', '-s', 'submitted', '-m 1'], r'\.\.\. change (\d+)'))

        if cl_number is None:
            return None

        return cl_number

    def get_or_create_changelist(self, description):
        ''' Creates or returns changelist number if it's not already created '''
        pending_changelists = self.get_pending_changelists()

        for cl_number in pending_changelists:
            pending_cl_desc = self.get_changelist_description(cl_number)

            assert pending_cl_desc is not None

            if description.lower() == pending_cl_desc.lower():
                return cl_number

        user = self.get_user()
        change_list_form = _CREATE_CHANGELIST_FORM_TEMPLATE.format(user        = user,
                                                                   workspace   = self.get_workspace(),
                                                                   description = description)

        for changelist, in self._parse_command_output(["change", "-i"], r"Change (\d+) created\.", stdin = change_list_form):
            return changelist

    def get_changelist_description(self, cl_number):
        ''' Returns description of given changelist '''
        desc, = next(self._parse_command_output(["describe", cl_number], r"\.\.\. desc (.*)"))
        return desc

    def get_changelist_author(self, cl_number):
        ''' Returs a tuple containing user, full name and email of the author of a changelist '''
        user, = next(self._parse_command_output(["describe", cl_number], r"\.\.\. user (.*)"))
        name, email = next(
            self._parse_command_output(
                ["users", user],
                r"\.\.\. FullName (.*)",
                r"\.\.\. Email (.*)"
            )
        )
        return user, name, email

    def get_pending_changelists(self):
        ''' Returns pending changelists '''
        workspace = self.get_workspace()
        assert isinstance(workspace, str)
        for changelist, in self._parse_command_output(["changes", "-c", workspace, "-s", "pending"], r"\.\.\. change (\d+)"):
            if changelist is not None:
                yield changelist

    def get_local_path(self, p4_path):
        ''' Returns local path of mapped given repository path'''
        local_path, = next(self._parse_command_output(['where', p4_path], r'\.\.\. path (.+)'))
        return local_path

    def get_user(self):
        ''' Returns current perforce user '''
        return next(self._parse_command_output(["user", "-o"], r"^\.\.\. User (.*)$"))[0]

    def get_workspace(self):
        ''' Returns current workspace '''
        workspace =  next(self._parse_command_output(["info"], r"^\.\.\. clientName (.*)$"))[0]
        if workspace == '*unknown*':
            return None
        return workspace

    def clean_files(self, path="//..."):
        ''' Cleans files in workspace not in depot, add missing files'''
        return self._run("clean", '-a', '-d', path) is not None

    def is_file_versioned(self, file_path):
        ''' Checks if a file is known by the source control '''
        command = self._get_p4_command("fstat", file_path)
        _, output, error = nimp.sys.process.call(command, capture_output=True)
        # Checks if the file was not added then deleted
        if re.search(r"\.\.\.\s*headAction\s*delete", output) is not None:
            return False
        return "no such file(s)" not in error and "file(s) not in client" not in error

    def revert(self, *files):
        ''' Reverts given files (regardless of the changelist they're edited in) '''
        files_to_revert = []
        for file_name, _, action in self.get_files_status(*files):
            if action != "edit":
                logging.debug("Ignoring not checked out file %s", file_name)
                continue
            logging.debug("Adding file %s to revert", file_name)
            files_to_revert.append(self._escape_filename(file_name))

        revert_input = '\n'.join(files_to_revert)
        output = self._run('-x', '-', "revert", stdin=revert_input) is None
        return output is not None

    def revert_changelist(self, cl_number):
        ''' Reverts given changelist '''
        output = self._run('revert', '-c', cl_number, '//...')
        return output is not None

    def revert_unchanged(self, cl_number):
        ''' Reverts unchanged files in given changelist '''
        output = self._run('revert', '-a', '-c', cl_number, '//...')
        return output is not None

    def submit(self, cl_number):
        ''' Submits given changelist '''
        logging.info("Submiting changelist %s...", cl_number)
        command = self._get_p4_command('submit', '-f', 'revertunchanged', '-c', cl_number)
        _, _, error = nimp.sys.process.call(command, capture_output=True)

        if error is not None and error != "":
            if "No files to submit." in error:
                logging.info("CL %s is empty, deleting it...", cl_number)
                return self.delete_changelist(cl_number)
            logging.error("%s", error)
            return False

        return True

    def sync(self, *files, cl_number = None, force=False):
        ''' Udpate given file '''
        command = ["sync"]

        if force:
            command += ['-f']

        file_list = [self._escape_filename(x) for x in files]
        if cl_number is not None:
            file_list = list(map(lambda x: '%s@%s' % (x, cl_number), file_list))

        command.extend(file_list)

        command = self._get_p4_command(*command)
        result, _, error = nimp.sys.process.call(command, capture_output=True, encoding='cp437')
        if (result != 0 or error != '') and 'file(s) up-to-date' not in error:
            return False

        return True

    def get_modified_files(self, *cl_numbers, root = '//...'):
        ''' Returns files modified by given changelists '''
        for cl_number in cl_numbers:
            for filename, action in self._parse_command_output(["fstat", "-e", cl_number , root],
                                                               r"^\.\.\. depotFile(.*)$",
                                                               r"^\.\.\. headAction(.*)"):
                filename = os.path.normpath(filename) if filename is not None else ''
                yield filename, action

    @staticmethod
    def _escape_filename(name):
        # As per https://www.perforce.com/perforce/r15.1/manuals/cmdref/filespecs.html
        return name.replace('%', '%25') \
                   .replace('@', '%40') \
                   .replace('#', '%23') \
                   .replace('*', '%2A')

    def _get_p4_command(self, *args):
        command = ['p4', '-z', 'tag']
        if self._port is not None:
            command += ['-p', self._port]
        if self._user is not None:
            command += ['-u', self._user]
        if self._password is not None:
            command += ['-P', self._password]
        if self._client is not None:
            command += ['-c', self._client]

        command += list(args)
        return command

    def _run(self, *args, stdin=None):
        command = self._get_p4_command(*args)

        for _ in range(5):
            result, output, error = nimp.sys.process.call(command, stdin=stdin, encoding='cp437', capture_output=True)

            if 'Operation took too long ' in error:
                continue

            has_fatal_errors = False
            if 'can\'t update' in error or \
               'can\'t clobber' in error or \
               'can\'t overwrite' in error:
                has_fatal_errors = True

            if result != 0 or has_fatal_errors:
                logging.info('p4 command failed: %s', error)
                return None

            return output

    def _parse_command_output(self, command, *patterns, stdin = None):
        output = self._run(*command, stdin = stdin)

        if output is not None:
            match_list = []

            for pattern in patterns:
                matches = list(re.finditer(pattern, output, re.MULTILINE))
                result = []
                for match in matches:
                    match_string = match.group(1)
                    match_string = match_string.strip()
                    result.append(match_string)
                match_list.append(result)

            for elem in zip(*match_list):
                yield elem
