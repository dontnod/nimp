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
import json
import os
import re
from pathlib import Path

import nimp.command
import nimp.utils.p4


class CreateLoadlist(nimp.command.Command):
	''' Generates a list of modified files from a set of Perforce changelists '''

	def configure_arguments(self, env, parser):
		parser.add_argument('changelists', nargs = '+', help = 'select the changelists to list files from')
		parser.add_argument('-o', '--output', help = 'output file')
		parser.add_argument('-e', '--extensions', nargs = '*', help = 'file extensions to include', default = [ 'uasset', 'umap' ])
		parser.add_argument('--check-empty', action = 'store_true', help = 'Returns check empty in json format')
		nimp.utils.p4.add_arguments(parser)
		return True

	def is_available(self, env):
		return env.is_unreal, ''

	def sanitized_changelists(self, env):
		changelists = set()
		# deal with possible nimp create-loadlist changelists '12 23 43' "23"
		for possible_cl_streak_string in env.changelists:
			changelists.update(re.sub(' +', ';', possible_cl_streak_string).split(';'))
		return [cl for cl in changelists if cl]

	def get_modified_files(self, env):
		changelists = self.sanitized_changelists(env)
		p4 = nimp.utils.p4.get_client(env)

		# Do not use '//...' which will also list files not mapped to workspace
		root = f"//{p4._client}/..."

		paths = []
		for cl in changelists:
			paths.append(f"{root}@{cl}")

		if len(paths) <= 0:
			paths.append(root)

		base_command = [
			"fstat",
			# Only list modified files currently accessible
			"-F", "^headAction=delete & ^headAction=move/delete"
		]

		modified_files = set()
		for (filepath, ) in p4._parse_command_output(base_command + paths, r"^\.\.\. clientFile(.*)$", hide_output=True):
			modified_files.add(os.path.normpath(filepath))

		return list(modified_files)


	def run(self, env):
		loadlist_files = []
		for filepath in self.get_modified_files(env):
			if f".{Path(filepath).suffix}" in env.extensions:
				loadlist_files.append(file)

		loadlist_path = env.output if env.output else f'{env.unreal_loadlist}'
		loadlist_path = os.path.abspath(env.format(nimp.system.sanitize_path(loadlist_path)))

		if env.check_empty:
			return self.check_empty_loadlist(loadlist_files)

		with open(env.format(loadlist_path), 'w+') as output:
			lines = output.readlines()
			for file in loadlist_files:
				if file not in lines:
					print(file)
					output.write(f'{file}\n')

		return True

	def check_empty_loadlist(self, modified_files):
		results = {'loadlist_is_empty': True}
		if modified_files:
			results['loadlist_is_empty'] = False

		json_content = json.dumps(results, indent=4)
		print('<loadlist_start>')
		print(json_content)
		print('<loadlist_end>')
		return True