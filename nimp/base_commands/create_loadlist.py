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

import os
import nimp.command

class CreateLoadlist(nimp.command.Command):
	''' Generates a list of modified files from a set of Perforce changelists '''

	def configure_arguments(self, env, parser):
		parser.add_argument('changelists', nargs = '+', help = 'select the changelists to list files from')
		parser.add_argument('-o', '--output', help = 'output file')
		parser.add_argument('-e', '--extensions', nargs = '*', help = 'file extensions to include', default = [ 'uasset', 'umap' ])
		nimp.utils.p4.add_arguments(parser)
		return True

	def is_available(self, env):
		return True, ''

	def run(self, env):
		p4 = nimp.utils.p4.get_client(env)

		modified_files = []
		for path, action in p4.get_modified_files(*env.changelists):
			file = os.path.basename(path)
			for extension in env.extensions:
				if file.endswith(extension):
					modified_files.append(file)
					break

		if env.output:
			with open(env.output, 'w') as output:
				for file in modified_files:
					output.write(f'{file}\n')
		else:
			for file in modified_files:
				print(file)

		return True
