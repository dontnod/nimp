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
import os
import nimp.command

class Automation(nimp.command.Command):
	''' Runs Unreal Automation Tests '''

	def configure_arguments(self, env, parser):
		parser.add_argument('tests', nargs = '*', help = 'list of test patterns to run')
		parser.add_argument('--loadlist', '-l', help = 'file containing a list of assets to check')
		parser.add_argument('--filter', '-f', default = 'All', help = 'Automation Framework filter to use')
		parser.add_argument('--dnefilter', action = 'store_true', help = 'use DNEAutomationTestFilter')
		parser.add_argument('--extra-options', help = 'extra arguments', nargs=argparse.REMAINDER, default = [])
		return True

	def is_available(self, env):
		return env.is_unreal, ''

	def run(self, env):
		extra_options = ['-stdout'] # this outputs command in console
		extra_options += env.extra_options

		dne_filter_cmd = 'dne.AutomationTestFilter 1, ' if env.dnefilter else ''

		tests = self.get_tests(env)
		tests_cmd = f"RunTests {'+'.join(tests)}" if tests else 'RunAll'

		cmd = f'{dne_filter_cmd}Automation SetFilter {env.filter}; {tests_cmd}; Quit'

		return nimp.unreal.unreal_cli(env, f'-execcmds={cmd}', *extra_options)

	def get_tests(self, env):
		tests = []
		if env.loadlist:
			env.loadlist = env.format(env.loadlist)
			with open(env.loadlist, 'r') as loadlist:
				for file in loadlist:
					tests.append(os.path.splitext(file)[0])
		tests.extend(env.tests[1:])
		return tests
