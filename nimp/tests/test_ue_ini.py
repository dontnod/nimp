# -*- coding: utf-8 -*-
# Copyright (c) 2014-2023 Dontnod Entertainment

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

''' UE .ini utilities unit tests '''

import unittest
import unittest.mock

import nimp.utils.ue_ini

class UpdateIniTests(unittest.TestCase):

    def test_simple(self):
        section_id = 'section'
        key_id = 'key'
        value = 'value'
        new_value = 'new_value'
        config = \
f'''\
[{section_id}]
{key_id}={value}
'''.splitlines(keepends=True)

        duplicate_config = nimp.utils.ue_ini.update_ini_file(list(config), section_id, (key_id, value))
        self.assertSequenceEqual(config, duplicate_config)

        new_config = nimp.utils.ue_ini.update_ini_file(list(config), section_id, (key_id, new_value))
        new_config_expected = list(config)
        new_config_expected[1] = f'{key_id}={new_value}\n'
        self.assertSequenceEqual(new_config_expected, new_config)

    def test_multiple_sections(self):
        section_id = 'section'
        key_id = 'key'
        value = 'value'
        config = \
f'''\
[{section_id}]
{key_id}={value}

[other_section]
other_key=other_value
'''.splitlines(keepends=True)

        duplicate_config = nimp.utils.ue_ini.update_ini_file(list(config), section_id, (key_id, value))
        self.assertSequenceEqual(config, duplicate_config)


    def test_no_keys(self):
        section_id = 'section'
        config = \
f'''\
[{section_id}]
key=value

[other_section]
other_key=other_value
'''.splitlines(keepends=True)

        duplicate_config = nimp.utils.ue_ini.update_ini_file(list(config), section_id)
        self.assertSequenceEqual(config, duplicate_config)
