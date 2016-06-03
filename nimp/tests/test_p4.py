# -*- coding: utf-8 -*-
# Copyright © 2014—2016 Dontnod Entertainment

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
''' System utilities unit tests '''

import contextlib
import os
import unittest
import unittest.mock
import argparse

import nimp.tests.utils
import nimp.p4

class _MockChangelist:
    def __init__(self, number, description):
        self.files = {}
        self.number = number
        self.description = description
        self.status = 'pending'

class P4Mock(nimp.tests.utils.MockCommand):
    ''' Mocks p4 command '''

    def __init__(self):
        super(P4Mock, self).__init__('p4')
        # Filename -> (action, head_action) dictionary)
        self._changelists = {}
        self._files = {}
        self._current_changelist = 0
        self._parser = argparse.ArgumentParser(prog = 'p4')
        self._init_args(self._parser)

    def add_changelist(self, description, *files_content):
        ''' Adds a fake changelist to this p4 mock '''
        if len(self._changelists) == 0:
            cl_number = '400'
        else:
            cl_number = str(int(max(self._changelists.keys(), key=int)) + 1)
        changelist = _MockChangelist(cl_number, description)
        changelist.status = 'submitted'
        self._changelists[cl_number] = changelist
        for filename, file_content in files_content:
            if filename not in self._files:
                self._files[filename] = []
            revisions = self._files[filename]
            new_rev = len(revisions)
            revisions.append(file_content)
            changelist.files[filename] = (new_rev, None)
        return cl_number

    def get_result(self, command, stdin = None):
        args = self._parser.parse_args(command)
        return args.command_to_run(args, stdin)

    def _init_args(self, parser):
        for flag in ['-z', '-c', '-H', '-p', '-P', '-u', '-x']:
            parser.add_argument(flag)

        subparsers  = parser.add_subparsers(title='Commands')
        P4Mock._init_infos(subparsers)
        P4Mock._init_user(subparsers)
        self._init_add(subparsers)
        self._init_change(subparsers)
        self._init_changes(subparsers)
        self._init_delete(subparsers)
        self._init_describe(subparsers)
        self._init_edit(subparsers)
        self._init_fstat(subparsers)
        self._init_reconcile(subparsers)
        self._init_revert(subparsers)
        self._init_submit(subparsers)
        self._init_sync(subparsers)

    def _get_file_status(self, filename):
        for _, change in reversed(sorted(self._changelists.items())):
            for name_it, (rev, local_status) in change.files.items():
                if name_it == filename:
                    head_revision = None
                    head_status = None
                    if name_it in self._files:
                        head_revision = self._files[name_it][rev]
                        head_status = 'delete' if head_revision is None else 'add'
                    return rev, head_status, local_status

        return 0, None, None

    def _init_add(self, subparsers):
        def _add_command(args, _):
            # TODO : Add ouput
            if args.changelist not in self._changelists:
                return (1, '', 'Changelist %s doesn\'t exists' % args.changelist)

            changelist = self._changelists[args.changelist]

            if changelist.status != 'pending':
                return (1, '', 'Change %s is already committed.' % args.changelist)

            for it in args.files:
                rev, _, _ = self._get_file_status(it)
                changelist.files[it] = (rev, 'add')
            return (0, '', '')

        parser = subparsers.add_parser('add')
        parser.add_argument('-c', '--changelist', default = 'default')
        parser.add_argument('files', nargs='+')
        parser.set_defaults(command_to_run = _add_command)

    def _init_change(self, subparsers):
        def _change_command(args, stdin):
            if hasattr(args, 'd') and args.d is not None:
                if args.d not in self._changelists:
                    return (1, '', 'Change %s unknown.' % args.d)
                change = self._changelists[args.d]
                if len(change.files) != 0:
                    error = 'Change %s has %i open file(s) associated with it and can\'t be deleted.'
                    error = error % (change.number, len(change.files))
                    return (1, '', error)
                del self._changelists[args.d]
                return (0, 'Change %s deleted.' % args.d, '')
            elif args.i:
                # TODO : Add better checks on C.L specification
                desc_lines = None
                for line in stdin.split('\n'):
                    if desc_lines is not None:
                        desc_lines.append(line.strip())
                    elif line.startswith('Description'):
                        desc_lines = []

                description = '\n'.join(desc_lines)
                if len(self._changelists) == 0:
                    cl_number = '400'
                else:
                    cl_number = str(int(max(self._changelists.keys(), key=int)) + 1)
                self._changelists[cl_number] = _MockChangelist(cl_number, description)
                return (0, 'Change %s created.' % cl_number, '')
            assert False, 'Not supported by mock'

        parser = subparsers.add_parser('change')
        parser.add_argument('-d')
        parser.add_argument('-i', action = 'store_true')
        parser.set_defaults(command_to_run = _change_command)

    def _init_changes(self, subparsers):
        def _changes_command(args, _):
            output = []
            change_id = 0
            for _, changelist in reversed(sorted(self._changelists.items())):
                if args.status is None or args.status.strip() == changelist.status:
                    template = ('... change %s\n'
                                '... time 1464522677\n'
                                '... user test_user\n'
                                '... client test_client\n'
                                '... status %s\n'
                                '... changeType public\n'
                                '... desc %s\n\n')
                    output.append(template % (changelist.number, changelist.status, changelist.description))
                if int(args.m) > 0 and change_id >= int(args.m):
                    break
                change_id += 1
            return (0, '\n\n'.join(output), '')

        parser = subparsers.add_parser('changes')
        parser.add_argument('-c', '--changes_client')
        parser.add_argument('-m', default = 0)
        parser.add_argument('-s', '--status', choices = ['pending', 'submitted', 'shelved'])
        parser.set_defaults(command_to_run = _changes_command)

    def _init_delete(self, subparsers):
        def _delete_command(args, stdin):
            if args.changelist not in self._changelists:
                return (1, '', 'Changelist %s doesn\'t exists' % args.changelist)

            changelist = self._changelists[args.changelist]

            if changelist.status != 'pending':
                return (1, '', 'Change %s is already committed.' % args.changelist)

            files = []
            if args.files is not None:
                files += args.files
            if stdin is not None:
                files += stdin.split('\n')
            for it in files:
                rev, _, _ = self._get_file_status(it)
                changelist.files[it] = (rev, 'delete')
                os.remove(it)
            return (0, '', '')

        parser = subparsers.add_parser('delete')
        parser.add_argument('-c', '--changelist', default = 'default')
        parser.add_argument('files', nargs='*')
        parser.set_defaults(command_to_run = _delete_command)

    def _init_describe(self, subparsers):
        def _describe_command(args, _):
            cl_number = args.changelist[0]
            changelist = self._changelists[cl_number]
            if cl_number not in self._changelists:
                return (1, '', '%s - no such changelist.' % cl_number)
            output = ('... change %s\n'
                      '... user test_user\n'
                      '... client test_client\n'
                      '... time 1464647491\n'
                      '... desc %s\n'
                      '... status pending\n'
                      '... changeType public\n\n') % (cl_number, changelist.description)
            file_id = 0
            for filename, (rev, local_action) in changelist.files.items():
                rel_path = os.path.relpath(filename, '/p4')
                output += '... depotFile%i //test_client/%s\n' % (file_id, rel_path)
                output += '... action%i %s\n' % (file_id, local_action)
                output += '... type%i binary\n' % file_id
                output += '... rev%i 1\n' % rev
                file_id += 1
            return (0, output, '')

        parser = subparsers.add_parser('describe')
        parser.add_argument('changelist', nargs = 1)
        parser.set_defaults(command_to_run = _describe_command)

    def _init_edit(self, subparsers):
        def _edit_command(args, stdin):
            if args.changelist not in self._changelists:
                return (1, '', 'Changelist %s doesn\'t exists' % args.changelist)
            changelist = self._changelists[args.changelist]

            if changelist.status != 'pending':
                return (1, '', 'Change %s is already committed.' % args.changelist)

            files = args.files + stdin.split('\n')
            stderr = []
            stdout = []
            result = 0
            for it in files:
                rev, head_status, _ = self._get_file_status(it)

                if head_status != 'add' or not os.path.exists(it):
                    stderr.append('%s - file(s) not on client.' % it)
                    continue

                changelist.files[it] = (rev, 'edit')
                rel_path = os.path.relpath(it, '/p4')
                stdout.append('//test_client/%s - opened for edit' % rel_path)

            result = 1 if len(stderr) != 0 else 0
            return (result, '\n'.join(stdout), '\n'.join(stderr))

        parser = subparsers.add_parser('edit')
        parser.add_argument('-c', '--changelist', default = 'default')
        parser.add_argument('files', nargs='*')
        parser.set_defaults(command_to_run = _edit_command)

    def _init_fstat(self, subparsers):
        def _get_file_fstat(filename):
            stdout = ''
            stderr = ''
            if not filename.startswith('/p4'):
                filename = os.path.join('/p4', filename)
            if filename.endswith('/...'):
                dirname = filename[:-4]
                for root, _, filenames in os.walk(dirname):
                    for child in filenames:
                        child_file = os.path.join(root, child)
                        child_file = os.path.relpath(child_file, '/p4')
                        file_stdout, file_stderr = _get_file_fstat(child_file)
                        stdout += file_stdout
                        stderr += file_stderr
            else:
                if not filename.startswith('/p4') :
                    return '', '%s - file(s) not in client view\n\n' % filename

                rev, head_status, local_status = self._get_file_status(filename)

                if head_status is None and local_status is None:
                    return '', '%s - no such file(s).\n\n' % filename

                stdout = ('... depotFile //test_client/%s\n'
                          '... clientFile %s\n'
                          '... isMapped\n'
                          '... headType text\n'
                          '... headTime 1462880462\n'
                          '... headRev %s\n'
                          '... headChange 408051\n'
                          '... headModTime 1454408928\n'
                          '... haveRev %s\n')
                stdout = stdout % (os.path.relpath(filename, '/p4'),
                                   filename,
                                   rev,
                                   rev)
                if head_status is not None:
                    stdout += '... headAction %s\n' % head_status
                if local_status is not None:
                    stdout += '... action %s\n' % local_status
                stdout += '\n'
            return stdout, stderr

        def _fstat_command(args, stdin):
            stdout = ''
            stderr = ''
            files = []

            if args.e is not None:
                files = [filename for filename, _ in self._changelists[args.e].files.items()]
            else:
                if args.files is not None:
                    files += args.files
                if stdin is not None:
                    files += stdin.split('\n')

            for it in files:
                file_stdout, file_stderr = _get_file_fstat(it)
                stdout += file_stdout
                stderr += file_stderr
            return (0, stdout, stderr)

        parser = subparsers.add_parser('fstat')
        parser.add_argument('-e')
        parser.add_argument('files', nargs='*')
        parser.set_defaults(command_to_run = _fstat_command)

    @staticmethod
    def _init_infos(subparsers):
        def _infos_command(*_):
            return (0,
                    ('... userName test_user\n'
                     '... clientName test_client\n'
                     '... clientRoot /p4root\n'
                     '... clientCwd /p4root\n'
                     '... clientHost test_host\n'),
                    '')
        parser = subparsers.add_parser('info')
        parser.set_defaults(command_to_run = _infos_command)

    def _init_reconcile(self, subparsers):
        def _reconcile_command(args, stdin):
            assert args.c in self._changelists
            changelist = self._changelists[args.c]
            paths_to_reconcile = stdin.split('\n')
            files_to_reconcile = set()

            for filename, _ in self._files.items():
                for path in paths_to_reconcile:
                    if path.startswith(filename):
                        files_to_reconcile.add(filename)

            for path in paths_to_reconcile:
                if path.endswith('/...'):
                    directory = path[:-4]
                    for root, _, filenames in os.walk(directory):
                        for child in filenames:
                            child_file = os.path.join(root, child)
                            files_to_reconcile.add(child_file)
                else:
                    files_to_reconcile.add(path)

            for file_it in files_to_reconcile:
                rev, head_action, action = self._get_file_status(file_it)
                if head_action != 'delete' and action != 'delete' and not os.path.exists(file_it):
                    changelist.files[file_it] = (rev, 'delete')
                    continue

                if not os.path.exists(file_it):
                    continue

                if head_action is None and action is None:
                    changelist.files[file_it] = (rev, 'add')
                    continue

                with open(file_it, 'r') as file:
                    file_content = file.read()

                if file_content != self._files[file_it][rev]:
                    changelist.files[file_it] = (rev, 'edit')

            return (0, '', '')

        parser = subparsers.add_parser('reconcile')
        parser.add_argument('-c')
        parser.set_defaults(command_to_run = _reconcile_command)

    def _init_revert(self, subparsers):
        def _revert(path, args):
            ''' Reverts given path '''
            if path == '//...':
                for cl_number, changelist in self._changelists.items():
                    if args.changelist is not None and cl_number != args.changelist:
                        continue
                    if changelist.status == 'pending':
                        for cl_file, _ in list(changelist.files.items()):
                            _revert(cl_file, args)
                        assert len(changelist.files) == 0
            else:
                for cl_number, changelist in self._changelists.items():
                    if args.changelist is not None and cl_number != args.changelist:
                        continue
                    if changelist.status == 'pending' and path in changelist.files:
                        del changelist.files[path]
                    rev, _, _ = self._get_file_status(path)
                    head_content = None
                    if path in self._files:
                        revisions = self._files[path]
                        if len(revisions) > rev and revisions[rev] is not None:
                            head_content = revisions[rev]

                    if args.a:
                        with open(path, 'r') as file_content:
                            if head_content is None or file_content.read() != head_content:
                                continue

                    if head_content is None:
                        os.remove(path)
                    else:
                        with open(path, 'w') as file_content:
                            file_content.write(head_content)

        def _revert_command(args, stdin):
            paths = []
            if args.paths is not None:
                paths += args.paths
            if stdin is not None:
                paths += stdin.split('\n')
            for path in paths:
                _revert(path, args)
            return (0, '', '')

        parser = subparsers.add_parser('revert')
        parser.add_argument('-c', '--changelist', default = None)
        parser.add_argument('-a', action = 'store_true')
        parser.add_argument('paths', nargs='*')
        parser.set_defaults(command_to_run = _revert_command)

    def _init_submit(self, subparsers):
        def _submit_command(args, _):
            if args.c is not None:
                assert args.c in self._changelists
                changelist = self._changelists[args.c]
                if len(changelist.files) == 0:
                    return (0, '', 'No files to submit.')
                for filename, (_, action) in changelist.files.items():
                    if action != 'delete':
                        with open(filename, 'r') as content_file:
                            content = content_file.read()
                    else:
                        content = None
                    if filename not in self._files:
                        self._files[filename] = []
                    revisions = self._files[filename]
                    rev_id = len(revisions)
                    revisions.append(content)
                    changelist.files[filename] = (rev_id, None)
                    changelist.status = 'submitted'
                return (0, '', '')
            return (1, '', '')

        parser = subparsers.add_parser('submit')
        parser.add_argument('-c')
        parser.add_argument('-f')
        parser.set_defaults(command_to_run = _submit_command)

    def _init_sync(self, subparsers):
        def _sync_command(args, _):
            filename = None
            revision = None
            synced_files = set()
            if args.file_range is not None:
                if '@' in args.file_range:
                    filename, revision = tuple(args.file_range.split('@'))
                else:
                    filename = None
                    revision = args.file_range
            for cl_number, change in reversed(sorted(self._changelists.items())):
                if revision is None or int(cl_number) <= int(revision):
                    for name_it, (rev, _) in change.files.items():
                        if filename is not None and filename != '' and name_it != filename:
                            continue

                        if name_it in synced_files:
                            continue

                        if name_it not in self._files:
                            continue


                        head_revision = self._files[name_it][rev]

                        if head_revision is None and os.path.exists(name_it):
                            os.remove(name_it)

                        elif head_revision is not None:
                            dirname = os.path.dirname(name_it)
                            nimp.system.safe_makedirs(dirname)
                            with open(name_it, 'w') as file_content:
                                file_content.write(head_revision)
                        synced_files.add(name_it)
            if revision is None:
                revision = str(int(max(self._changelists.keys(), key=int)))
            self._current_changelist = revision
            return (0, '', '')

        parser = subparsers.add_parser('sync')
        parser.add_argument('-f')
        parser.add_argument('file_range', nargs='?')
        parser.set_defaults(command_to_run = _sync_command)

    @staticmethod
    def _init_user(subparsers):
        def _user_command(args, _):
            if args.o:
                return (0,
                        ('... User test_user'
                         '... Email test@test.test'
                         '... Update 2013/06/12 15:33:16'
                         '... Access 2016/05/31 00:09:46'
                         '... FullName Test User'
                         '... Password ******'
                         '... Type standard'),
                        '')
            assert False, 'Not supported by mock'

        parser = subparsers.add_parser('user')
        parser.add_argument('-o', action ='store_true')
        parser.set_defaults(command_to_run = _user_command)

@contextlib.contextmanager
def mock_p4():
    ''' Returns a p4 mock '''
    with nimp.tests.utils.mock_filesystem():
        p4_mock = P4Mock()
        with nimp.tests.utils.mock_capture_process_output(p4_mock):
            yield p4_mock

class _P4Tests(unittest.TestCase):
    def __init__(self, test):
        super(_P4Tests, self).__init__(test)
        self._p4 = nimp.p4.P4(host = 'test_host',
                              user = 'test_user',
                              password = 'test_password',
                              client = 'test_client')

    def _assert_action_is(self, filename, action):
        files_status = list(self._p4.get_files_status(filename))
        self.assertTrue(len(files_status) == 1)
        self.assertEqual(files_status[0][2], action)

    def _assert_head_action_is(self, filename, head_action):
        files_status = list(self._p4.get_files_status(filename))
        self.assertTrue(len(files_status) == 1)
        self.assertEqual(files_status[0][1], head_action)

    def test_add(self):
        ''' Checks if adding files to perforce is working '''
        with mock_p4():
            nimp.tests.utils.create_file('/p4/file_1', 'rev_1')
            nimp.tests.utils.create_file('/p4/file_2', 'rev_1')
            cl_number = self._p4.get_or_create_changelist('test_cl')
            self.assertIsNotNone(cl_number)

            self.assertTrue(self._p4.add(cl_number, '/p4/file_1'))
            self._assert_action_is('/p4/file_1', 'add')

            self.assertTrue(self._p4.submit(cl_number))

            self.assertFalse(self._p4.add(cl_number, '/p4/file_2'))
            self.assertFalse(self._p4.add('999999', '/p4/file_2'))

    def test_delete(self):
        ''' deletes should delete files '''
        with mock_p4() as mock:
            mock.add_changelist('test changelist',
                                ('/p4/file_1', 'rev 1'),
                                ('/p4/file_2', 'rev 1'))
            self._p4.sync()
            cl_number = self._p4.get_or_create_changelist('test_cl')
            self.assertIsNotNone(cl_number)

            self.assertTrue(self._p4.delete(cl_number, '/p4/file_1'))
            self._assert_action_is('/p4/file_1', 'delete')
            self.assertFalse(os.path.exists('/p4/file_1'))
            self.assertTrue(self._p4.submit(cl_number))
            self.assertFalse(self._p4.delete(cl_number, '/p4/file_2'))
            self.assertFalse(self._p4.delete('9999999', '/p4/file_2'))

    def test_clean_workspace(self):
        ''' clean_workspace should revert all files and delete pending changelist '''
        with mock_p4() as mock:
            mock.add_changelist('test changelist',
                                ('/p4/file_1', 'rev_1'),
                                ('/p4/file_2', 'rev_2'),
                                ('/p4/file_3', 'rev_1'))
            self._p4.sync()

            cl_number = self._p4.get_or_create_changelist('test changelist')
            self._p4.edit(cl_number, '/p4/file_1')

            cl_number = self._p4.get_or_create_changelist('test changelist 2')
            self._p4.edit(cl_number, '/p4/file_2')

            self.assertTrue(self._p4.clean_workspace())
            pending_cls = self._p4.get_pending_changelists()

            self.assertTrue(len(list(pending_cls)) == 0)
            self._assert_action_is('/p4/file_1', None)
            self._assert_action_is('/p4/file_2', None)
            self._assert_action_is('/p4/file_3', None)

    def test_get_or_create_changelist(self):
        ''' get_or_create_changelist should create a new changelist '''
        with mock_p4():
            self.assertListEqual([], list(self._p4.get_pending_changelists()))
            cl_number = self._p4.get_or_create_changelist('changelist description')
            pending_cls = self._p4.get_pending_changelists()
            description = self._p4.get_changelist_description(cl_number)

            self.assertListEqual(list(pending_cls), [cl_number])
            self.assertEqual('changelist description', description)

            already_existing_cl = self._p4.get_or_create_changelist('changelist description')
            self.assertEqual(already_existing_cl, cl_number)

    def test_delete_changelist(self):
        ''' delete_changelist should delete pending changelist '''
        with mock_p4():
            cl_number = self._p4.get_or_create_changelist('changelist description')
            self.assertTrue(self._p4.delete_changelist(cl_number))
            self.assertListEqual([], list(self._p4.get_pending_changelists()))

            nimp.tests.utils.create_file('/p4/file', 'rev 1')
            cl_number = self._p4.get_or_create_changelist('changelist description')
            self.assertTrue(self._p4.add(cl_number, '/p4/file'))
            self.assertFalse(self._p4.delete_changelist(cl_number))

            self.assertFalse(self._p4.delete_changelist('999999999'))

    def test_get_files_status(self):
        ''' get_file_status should return correct file status '''
        # /... should be added to the end of a file if it's a directory
        with mock_p4() as mock:
            mock.add_changelist('test changelist',
                                ('/p4/file_1', 'rev_1'),
                                ('/p4/file_2', 'rev_1'),
                                ('/p4/file_3', 'rev_1'),
                                ('/p4/dir/child_1', 'rev_1'))

            mock.add_changelist('test changelist 2',
                                ('/p4/file_2', None),
                                ('/p4/file_3', None),
                                ('/p4/dir/child_1', 'rev_2'))

            self._p4.sync()
            nimp.tests.utils.create_file('/p4/dir/child_2', 'rev_1')
            nimp.tests.utils.create_file('/p4/dir/child_3', 'rev_1')
            nimp.tests.utils.create_file('/some_path/not_in_client', 'rev_1')

            cl_number = self._p4.get_or_create_changelist('test changelist')
            self._p4.edit(cl_number, '/p4/file_1')
            self._p4.add(cl_number, '/p4/file_2')
            self._p4.add(cl_number, '/p4/dir/child_2')

            result = self._p4.get_files_status('/p4/dir',
                                               '/p4/file_1',
                                               '/p4/file_2',
                                               '/p4/file_3',
                                               '/some_path/not_in_client',
                                               '/p4/unknown_file')

            expected = [('/p4/dir/child_1', 'add', None),
                        ('/p4/dir/child_2', None, 'add'),
                        ('/p4/file_1', 'add', 'edit'),
                        ('/p4/file_2', 'delete', 'add'),
                        ('/p4/file_3', 'delete', None)]

            self.assertListEqual(list(result), expected)

    def test_edit(self):
        ''' edit should open correct files for edit'''
        with mock_p4() as mock:
            mock.add_changelist('test_changelist',
                                ('/p4/file_1', 'rev_1'),
                                ('/p4/file_2', 'rev_1'))

            mock.add_changelist('test_changelist',
                                ('/p4/file_1', 'rev_1'),
                                ('/p4/file_2', None))
            self._p4.sync()

            cl_number = self._p4.get_or_create_changelist('test changelist')
            self.assertTrue(self._p4.edit(cl_number, '/p4/file_1', '/p4/file_2'))

            self._assert_action_is('/p4/file_1', 'edit')
            self._assert_action_is('/p4/file_2', None)

            self.assertTrue(self._p4.submit(cl_number))
            self.assertFalse(self._p4.edit(cl_number, '/p4/file_1'))
            self.assertFalse(self._p4.edit(cl_number, '/p4/file_1'))
            self.assertFalse(self._p4.edit(cl_number, '/p4/file_2'))

    def test_reconcile(self):
        ''' reconcile should get a coherent workspace status '''
        # files opened for edit and deleted on disk should be reverted then
        # deleted in perforce in order to have a good state
        with mock_p4() as mock:
            mock.add_changelist('test_changelist',
                                ('/p4/file_1', 'rev 1'),
                                ('/p4/file_2', 'rev 1'),
                                ('/p4/file_3', 'rev 1'),
                                ('/p4/dir/file_1', 'rev 1'))
            self._p4.sync()

            cl_number = self._p4.get_or_create_changelist('Test changelist')

            self.assertTrue(self._p4.edit(cl_number, '/p4/file_2'))

            os.remove('/p4/file_1')
            os.remove('/p4/file_2')

            with open('/p4/file_3', 'w') as file_content:
                file_content.write('rev 2')

            nimp.tests.utils.create_file('/p4/dir/file_2', 'rev 1')

            self.assertTrue(self._p4.reconcile(cl_number, '/p4/dir', '/p4/file_1', '/p4/file_2', '/p4/file_3'))
            status = self._p4.get_files_status('/p4/dir', '/p4/file_1', '/p4/file_2', '/p4/file_3')

            self.assertListEqual(list(status),
                                 [('/p4/dir/file_1', 'add', None),
                                  ('/p4/dir/file_2', None, 'add'),
                                  ('/p4/file_1', 'add', 'delete'),
                                  ('/p4/file_2', 'add', 'delete'),
                                  ('/p4/file_3', 'add', 'edit')])

    def test_describe(self):
        ''' describe should return changelist description'''
        # files opened for edit and deleted on disk should be reverted then
        # deleted in perforce in order to have a good state
        with mock_p4():
            cl_number = self._p4.get_or_create_changelist('test description')
            result = self._p4.get_changelist_description(cl_number)
            self.assertEqual(result, 'test description')

    def test_sync(self):
        ''' describe should return changelist description'''
        with mock_p4() as mock:
            rev_1 = mock.add_changelist('test_changelist',
                                        ('/p4/file_1', 'rev 1'),
                                        ('/p4/file_2', 'rev 1'),
                                        ('/p4/file_3', 'rev 1'))
            rev_2 = mock.add_changelist('test_changelist',
                                        ('/p4/file_1', 'rev 2'),
                                        ('/p4/file_2', 'rev 2'),
                                        ('/p4/file_3', 'rev 2'))
            mock.add_changelist('test_changelist',
                                ('/p4/file_2', None),
                                ('/p4/file_3', 'rev 3'))
            self._p4.sync(rev_1)
            self._p4.sync()

            self.assertTrue(os.path.exists('/p4/file_1'))
            self.assertFalse(os.path.exists('/p4/file_2'))
            self.assertTrue(os.path.exists('/p4/file_3'))

            with open('/p4/file_1', 'r') as file_content:
                self.assertEqual(file_content.read(), 'rev 2')

            with open('/p4/file_3', 'r') as file_content:
                self.assertEqual(file_content.read(), 'rev 3')

            self._p4.sync('/p4/file_3', rev_2)

            with open('/p4/file_1', 'r') as file_content:
                self.assertEqual(file_content.read(), 'rev 2')

            with open('/p4/file_3', 'r') as file_content:
                self.assertEqual(file_content.read(), 'rev 2')

            self._p4.sync(cl_number = rev_1)

            self.assertTrue(os.path.exists('/p4/file_1'))
            self.assertTrue(os.path.exists('/p4/file_2'))
            self.assertTrue(os.path.exists('/p4/file_3'))

            with open('/p4/file_1', 'r') as file_content:
                self.assertEqual(file_content.read(), 'rev 1')

            with open('/p4/file_2', 'r') as file_content:
                self.assertEqual(file_content.read(), 'rev 1')

            with open('/p4/file_3', 'r') as file_content:
                self.assertEqual(file_content.read(), 'rev 1')

    def test_is_file_versionned(self):
        ''' describe should return changelist description'''
        with mock_p4() as mock:
            mock.add_changelist('test_changelist',
                                ('/p4/file_1', 'rev 1'),
                                ('/p4/file_2', 'rev 1'),
                                ('/p4/file_3', 'rev 1'))

            mock.add_changelist('test_changelist',
                                ('/p4/file_2', None),
                                ('/p4/file_3', None))

            mock.add_changelist('test_changelist',
                                ('/p4/file_3', 'recreated'))

            self._p4.sync()
            nimp.tests.utils.create_file('/p4/file_4', 'rev 1')

            self.assertTrue(self._p4.is_file_versioned('/p4/file_1'))
            self.assertFalse(self._p4.is_file_versioned('/p4/file_2'))
            self.assertTrue(self._p4.is_file_versioned('/p4/file_3'))
            self.assertFalse(self._p4.is_file_versioned('/p4/file_4'))

    def test_get_last_synced_changelist(self):
        ''' describe should return changelist description'''
        with mock_p4() as mock:
            mock.add_changelist('test_changelist', ('/p4/file_1', 'rev 1'))
            cl_number = mock.add_changelist('test_changelist', ('/p4/file_1', 'rev 2'))
            self._p4.sync()
            self.assertEqual(self._p4.get_last_synced_changelist(), cl_number)

    def test_revert_changelist(self):
        ''' should rever only files in specified changelist '''
        with mock_p4() as mock:
            mock.add_changelist('test_changelist',
                                ('/p4/file_1', 'rev 1'),
                                ('/p4/file_2', 'rev 1'))

            self._p4.sync()
            cl_1 = self._p4.get_or_create_changelist('test cl_1')
            cl_2 = self._p4.get_or_create_changelist('test cl_2')

            self._p4.edit(cl_1, '/p4/file_1')
            self._p4.edit(cl_2, '/p4/file_2')

            with open('/p4/file_1', 'w') as file_content:
                file_content.write('rev 2')

            with open('/p4/file_2', 'w') as file_content:
                file_content.write('rev 2')

            self.assertTrue(self._p4.revert_changelist(cl_1))

            with open('/p4/file_1', 'r') as file_content:
                self.assertEqual(file_content.read(), 'rev 1')

            with open('/p4/file_2', 'r') as file_content:
                self.assertEqual(file_content.read(), 'rev 2')

    def test_revert_unchanged(self):
        ''' should rever only files in specified changelist that have not changed '''
        with mock_p4() as mock:
            mock.add_changelist('test_changelist',
                                ('/p4/file_1', 'rev 1'),
                                ('/p4/file_2', 'rev 1'))

            self._p4.sync()
            changelist  = self._p4.get_or_create_changelist('test changelist')

            self._p4.edit(changelist, '/p4/file_1')
            self._p4.edit(changelist, '/p4/file_2')

            with open('/p4/file_1', 'w') as file_content:
                file_content.write('rev 2')

            self.assertTrue(self._p4.revert_unchanged(changelist))

            self._assert_action_is('/p4/file_1', None)
            self._assert_action_is('/p4/file_2', None)

    def test_submit(self):
        ''' test submit '''
        with mock_p4():
            changelist  = self._p4.get_or_create_changelist('test changelist')

            nimp.tests.utils.create_file('/p4/file_1', 'rev 1')
            self._p4.add(changelist, '/p4/file_1')

            self.assertTrue(self._p4.submit(changelist))

            self._assert_action_is('/p4/file_1', None)
            self._assert_head_action_is('/p4/file_1', 'add')

            changelist  = self._p4.get_or_create_changelist('test changelist')
            self.assertTrue(self._p4.submit(changelist))

    def test_get_modified_files(self):
        ''' test submit '''
        with mock_p4() as mock:
            cl_1 = mock.add_changelist('test_changelist',
                                       ('/p4/file_1', 'rev 1'),
                                       ('/p4/file_2', 'rev 1'),
                                       ('/p4/file_3', 'rev 1'))

            cl_2 = mock.add_changelist('test_changelist',
                                       ('/p4/file_2', 'rev 2'),
                                       ('/p4/file_3', None))

            cl_3 = mock.add_changelist('test_changelist',
                                       ('/p4/file_3', 'recreated'))

            cl_1_modified_files = list(self._p4.get_modified_files(cl_1))
            cl_2_modified_files = list(self._p4.get_modified_files(cl_2))
            cl_3_modified_files = list(self._p4.get_modified_files(cl_3))

            self.assertListEqual([('/test_client/file_1', 'add'),
                                  ('/test_client/file_2', 'add'),
                                  ('/test_client/file_3', 'add')],
                                 sorted(cl_1_modified_files))

            self.assertListEqual([('/test_client/file_2', 'add'),
                                  ('/test_client/file_3', 'add')],
                                 sorted(cl_2_modified_files))

            self.assertListEqual([('/test_client/file_3', 'add')],
                                 sorted(cl_3_modified_files))



