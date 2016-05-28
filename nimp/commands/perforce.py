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
''' Perforce related commands '''

import abc

import nimp.commands.command
import nimp.p4

class P4Command(nimp.commands.command.Command):
    ''' Perforce command base class '''

    def __init__(self):
        super(P4Command, self).__init__()

    def configure_arguments(self, env, parser):
        # These are not marked required=True because sometimes we don’t
        # really need them.
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

        return True

    @abc.abstractmethod
    def sanitize(self, env):
        ''' Validates and sanitize environment before executing command'''
        pass

    @abc.abstractmethod
    def run(self, env):
        ''' Executes the command '''
        pass

class P4CleanWorkspace(P4Command):
    ''' Reverts all files and deletes all pending changelists.'''
    def __init__(self):
        super(P4CleanWorkspace, self).__init__()

    def sanitize(self, env):
        if hasattr(env, 'arg') and env.arg is not None:
            for key_value in env.arg:
                setattr(env, key_value[0], key_value[1])
        env.standardize_names()
        return True

    def run(self, env):
        if not nimp.p4.clean_workspace():
            return False

#   def _register_prepare_workspace(subparsers):
#       def _execute(env):
#           if not nimp.p4.create_config_file(env.p4port, env.p4user, env.p4pass, env.p4client):
#               return False
#
#           if env.patch_config is not None and env.patch_config != "None":
#               if not env.load_config_file(env.patch_config):
#                   logging.error("Error while loading patch config file %s, aborting...", env.patch_config)
#                   return False
#
#               for file_path, revision in env.patch_files_revisions:
#                   log_notification("Syncing file {0} to revision {1}", file_path, revision)
#                   if not p4_sync(file_path, revision):
#                       return False
#
#                   if file_path == ".nimp.conf":
#                       log_notification("Reloading config...")
#                       if not env.load_config_file(".nimp.conf"):
#                           return False
#           return True
#
#       parser = subparsers.add_parser("prepare-workspace", help = "Writes a .p4config file and removes all pending CLs from workspace")
#
#
#       parser.add_argument("--patch-config",
#                           help = "Path to the patch config file",
#                           metavar = "<FILE>",
#                           default = "None")
#
#       parser.set_defaults(p4_command_to_run = _execute)
#
#   #---------------------------------------------------------------------------
#   def _register_clean_workspace(self, subparsers):
#       def _execute(env):
#           return p4_clean_workspace()
#
#       parser = subparsers.add_parser("clean-workspace", help = "Reverts and delete all pending changelists.")
#       parser.set_defaults(p4_command_to_run = _execute)
#
#
#   #---------------------------------------------------------------------------
#   def _register_checkout(self, subparsers):
#       _register_fileset_command(subparsers , "checkout", "Checks out a fileset", p4_edit)
#
#   #---------------------------------------------------------------------------
#   def _register_reconcile(self, subparsers):
#       _register_fileset_command(subparsers, "reconcile", "Reconciles a fileset", p4_reconcile)
#
#   #---------------------------------------------------------------------------
#   def _register_submit(self, subparsers):
#       def _execute(env):
#           cl_number = p4_get_or_create_changelist(env.format(env.cl_name))
#
#           if cl_number is None:
#               return False
#
#           return p4_submit(cl_number)
#
#       parser = subparsers.add_parser("submit",
#                                      help = "Reconciles a fileset")
#       parser.add_argument('cl_name', metavar = '<FORMAT>', type = str, default = None)
#       parser.add_argument('--arg', help = 'DEPRECATED, DO NOT USE', nargs = 2, action = 'append', default = [])
#       parser.set_defaults(p4_command_to_run = _execute)
#
#---------------------------------------------------------------------------
#ef _register_fileset_command(subparsers, command_name, help, p4_func):
#   def _execute(env):
#       cl_number = p4_get_or_create_changelist(env.format(env.cl_name))
#
#       if cl_number is None:
#           return False
#
#       if env.fileset:
#           files = env.map_files()
#           if files.load_set(env.format(env.p4_path)) is None:
#               return False
#           files = [file[0] for file in files()]
#       else:
#           files = [env.format(env.p4_path)]
#
#       return p4_func(cl_number, *files)
#   parser = subparsers.add_parser(command_name,
#                                  help = help)
#   parser.add_argument('cl_name', metavar = '<STR>', type = str)
#   parser.add_argument('p4_path', metavar = '<PATH>', type = str)
#   parser.add_argument('--fileset',
#                       help    = "Handle path as a fileset, not a regular path.",
#                       action  = "store_true",
#                       default = False)
#   parser.add_argument('--arg',
#                       help    = 'Specify interpolation arguments to set while checking out.',
#                       nargs=2,
#                       action='append',
#                       default = [])
#   parser.set_defaults(p4_command_to_run = _execute)
