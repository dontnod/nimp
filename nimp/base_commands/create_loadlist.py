# -*- coding: utf-8 -*-
# Copyright (c) 2014-2022 Dontnod Entertainment

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
import argparse
import fnmatch
import itertools
import logging
import os

import nimp.command
import nimp.utils.p4


class CreateLoadlist(nimp.command.Command):
    '''Generates a list of modified files from a set of Perforce changelists'''

    def configure_arguments(self, env, parser):
        parser.add_argument(
            'changelists',
            nargs=argparse.ZERO_OR_MORE,
            help='select the changelists to list files from. Defaults to listing all files in havelist',
            default=[],
        )
        parser.add_argument('-o', '--output', help='output file')
        parser.add_argument(
            '-e',
            '--extensions',
            nargs=argparse.ZERO_OR_MORE,
            help='file extensions to include',
            default=['uasset', 'umap'],
        )
        parser.add_argument(
            '--dirs', nargs=argparse.ZERO_OR_MORE, help='directories to include', default=['//{p4client}/...']
        )
        parser.add_argument('--exclude-dirs', nargs=argparse.ZERO_OR_MORE, help='directories to exclude', default=None)
        parser.add_argument('--error-on-empty', action='store_true', help='return an error code if loadlist is empty')
        nimp.utils.p4.add_arguments(parser)
        nimp.command.add_common_arguments(parser, 'dry_run', 'slice_job')
        return True

    def is_available(self, env):
        return env.is_unreal, ''

    @staticmethod
    def _product_dirs_and_extensions(env, extensions):
        if env.dirs is None:
            env.dirs = ['']
        dirs = [env.format(dir) for dir in env.dirs]
        return list(itertools.product(dirs, extensions))

    @staticmethod
    def _product_paths_and_changelists(env, paths):
        changelists = [f'@{cl},{cl}' for cl in env.changelists]
        if len(changelists) <= 0:
            changelists = ['#have']
        return list(itertools.product(paths, changelists))

    @staticmethod
    def _exclude_from_modified_files(exclude_dirs, filepath):
        if exclude_dirs is None:
            return False
        for exclude_dir in exclude_dirs:
            if fnmatch.fnmatch(filepath, f'*{exclude_dir}*'):
                return True
        return False

    @staticmethod
    def _normpath_dirs(dirs):
        if dirs is None:
            return dirs
        return [os.path.normpath(dir) for dir in dirs]

    def get_modified_files(self, env, extensions):
        p4 = nimp.utils.p4.get_client(env)

        paths = []
        for dir, ext in self._product_dirs_and_extensions(env, extensions):
            paths.append(f"{dir}{ext}")

        filespecs = []
        for path, cl in self._product_paths_and_changelists(env, paths):
            filespecs.append(f"{path}{cl}")

        self.has_deleted_files = False
        p4_deleted_files_command = ["fstat", "-F", "headAction=delete"]
        for (filepath,) in p4._parse_command_output(
            p4_deleted_files_command + filespecs, r"^\.\.\. depotFile(.*)$", hide_output=True, encoding='utf-8'
        ):
            if not self.has_deleted_files:
                self.has_deleted_files = True
                logging.debug('file deletions not considered for loadlist')
            logging.debug(filepath)

        base_command = [
            "fstat",
            # Only list modified files currently accessible
            "-F",
            "^headAction=delete & ^headAction=move/delete",
        ]

        modified_files = set()
        exclude_dirs = self._normpath_dirs(env.exclude_dirs)
        for (filepath,) in p4._parse_command_output(
            base_command + filespecs, r"^\.\.\. clientFile(.*)$", hide_output=True, encoding='utf-8'
        ):
            modified_file_path = os.path.normpath(filepath)
            if not self._exclude_from_modified_files(exclude_dirs, modified_file_path):
                modified_files.add(modified_file_path)

        # Needed for sorting and ease debug
        modified_files = list(modified_files)
        modified_files.sort()

        if env.slice_job_count is not None and env.slice_job_count > 1:
            # slice modified files
            # use a simple heuristic to spread the load between slices
            # as demanding files tends to be in the same directory
            slice = []
            for idx, elem in enumerate(modified_files):
                if (idx % env.slice_job_count) == (env.slice_job_index - 1):
                    slice.append(elem)

            modified_files = slice

        return modified_files

    def run(self, env):
        loadlist_files = self.get_modified_files(env, env.extensions)

        loadlist_path = env.output if env.output else f'{env.unreal_loadlist}'
        loadlist_path = os.path.abspath(env.format(nimp.system.sanitize_path(loadlist_path)))

        if not env.dry_run:
            with open(loadlist_path, 'w') as fp:
                for file in loadlist_files:
                    print(file)
                    fp.write(f'{file}\n')

        if env.error_on_empty:
            logging.info("Empty loadlist: no work needed.")
            if self.has_deleted_files:
                logging.debug("Loadlist is empty because submits contain only deleted files.")
            logging.debug("Command will fail because --error-on-empty enabled.")
            return len(loadlist_files) > 0

        return True
