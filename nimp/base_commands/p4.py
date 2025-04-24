# -*- coding: utf-8 -*-
# Copyright (c) 2014-2019 Dontnod Entertainment

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

'''Perforce related commands.'''

import abc
import shutil

import nimp.command
import nimp.utils.p4


def _is_p4_available():
    if shutil.which('p4') is None:
        return False, ('p4 executable was not found on your system, check your installation.')
    return True, ''


class P4Command(nimp.command.Command):
    '''Perforce command base class'''

    def __init__(self):
        super(P4Command, self).__init__()

    def configure_arguments(self, env, parser):
        pass

    def is_available(self, env):
        return _is_p4_available()

    @abc.abstractmethod
    def run(self, env):
        '''Executes the command'''
        pass


class P4(nimp.command.CommandGroup):
    '''Run Perforce commands'''

    def __init__(self):
        super(P4, self).__init__([_RevertWorkspace(), _Submit(), _Fileset()])

    def configure_arguments(self, env, parser):
        super(P4, self).configure_arguments(env, parser)
        nimp.utils.p4.add_arguments(parser)

    def is_available(self, env):
        return _is_p4_available()


class _RevertWorkspace(P4Command):
    '''Reverts and deletes all pending changelists'''

    def __init__(self):
        super(_RevertWorkspace, self).__init__()

    def is_available(self, env):
        return _is_p4_available()

    def run(self, env):
        if not nimp.utils.p4.check_for_p4(env):
            return False

        p4 = nimp.utils.p4.get_client(env)
        return p4.clean_workspace()


class _Fileset(P4Command):
    '''Runs perforce commands operation on a fileset.'''

    def __init__(self):
        super(_Fileset, self).__init__()

    def configure_arguments(self, env, parser):
        # These are not marked required=True because sometimes we don’t
        # really need them.
        super(_Fileset, self).configure_arguments(env, parser)

        parser.add_argument(
            'p4_operation',
            help='Operation to perform on the fileset.',
            choices=['checkout', 'revert', 'reconcile', 'sync'],
        )

        parser.add_argument('fileset', metavar='<fileset>', help='Fileset to load.')

        parser.add_argument(
            'changelist_description',
            metavar='<description>',
            help='Changelist description format, will be interpolated with environment value.',
        )

        nimp.command.add_common_arguments(parser, 'platform', 'configuration', 'target', 'revision', 'free_parameters')
        return True

    def is_available(self, env):
        return _is_p4_available()

    def run(self, env):
        if not nimp.utils.p4.check_for_p4(env):
            return False

        p4 = nimp.utils.p4.get_client(env)

        # Dictionary below has the following structure:
        # key: p4_operation
        # value: [method, uses_a_changelist]
        operations = {
            'checkout': [p4.edit, True],
            'reconcile': [p4.reconcile, True],
            'revert': [p4.revert, False],
            'sync': [p4.sync, False],
        }

        files = nimp.system.map_files(env)
        if files.load_set(env.fileset) is None:
            return False
        files = [file[0] for file in files()]

        if operations[env.p4_operation][1]:
            if env.changelist_description == 'default':
                changelist = 'default'
            else:
                description = env.format(env.changelist_description)
                changelist = p4.get_or_create_changelist(description)
            return operations[env.p4_operation][0](changelist, *files)
        else:
            return operations[env.p4_operation][0](*files)


class _Submit(P4Command):
    '''Submits a changelist identified by its description'''

    def __init__(self):
        super(_Submit, self).__init__()

    def configure_arguments(self, env, parser):
        # These are not marked required=True because sometimes we don’t
        # really need them.
        super(_Submit, self).configure_arguments(env, parser)

        parser.add_argument(
            'changelist_description',
            metavar='<description>',
            help='Changelist description format, will be interpolated with environment value.',
        )

        return True

    def is_available(self, env):
        return _is_p4_available()

    def run(self, env):
        if not nimp.utils.p4.check_for_p4(env):
            return False

        p4 = nimp.utils.p4.get_client(env)

        description = env.format(env.changelist_description)
        changelist = p4.get_or_create_changelist(description)

        return p4.submit(changelist)
