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

''' System utilities unit tests '''

import os
import itertools
import unittest

import nimp.tests.utils
import nimp.system

def _file_mapper(**format_args):
    mapper = nimp.system.FileMapper(mapper=_yield_mapper,
                                    format_args=format_args)

    return mapper, mapper.src("mocks/file_mapper_tests").to('.')

def _yield_mapper(src, destination):
    if src is not None:
        src = os.path.normpath(src)

    if destination is not None:
        destination = os.path.normpath(destination)

    yield src, destination

class _FileSetTests(unittest.TestCase):
    def __init__(self, methodName='runTest'):
        super(_FileSetTests, self).__init__(methodName)

    def _check_files(self, mapper_files, *expected_files):
        abs_expected_files = []
        for src, dst in expected_files:
            expected_src = os.path.normpath(os.path.join("mocks/file_mapper_tests", src))
            abs_expected_files.append((expected_src, os.path.normpath(dst)))
        self.assertListEqual(list(mapper_files), abs_expected_files)

    def test_call(self):
        ''' Calling a file mapper with a simple file name should process it.'''
        files, src = _file_mapper(qux='qux.ext1')
        src.glob('{qux}')
        self._check_files(files(), ('qux.ext1', 'qux.ext1'))

    def test_dst(self):
        ''' To should translate target directory '''
        files, src = _file_mapper(dir='dest')
        src.to("{dir}").glob('qux.ext1')
        self._check_files(files(), ('qux.ext1', 'dest/qux.ext1'))

    def test_empty_call(self):
        ''' Calling a file mapper with no argument should process empty path.'''
        files, _ = _file_mapper()
        self._check_files(files(), ('', ''))

    def test_exclude(self):
        ''' Exclude should remove files matching one of the given patterns.  '''
        files, src = _file_mapper()
        src.glob('foo/bar/corge.ext1', 'foo/bar/corge.ext2').exclude('*.ext2')
        self._check_files(files(), ('foo/bar/corge.ext1', 'foo/bar/corge.ext1'))

    def test_exclude_ignore_case(self):
        ''' Exclude should remove files matching one of the given patterns.  '''
        files, src = _file_mapper()
        src.glob('foo/bar/corge.ext1', 'foo/bar/corge.ext2').exclude_ignore_case('*rGE.ext2')
        self._check_files(files(), ('foo/bar/corge.ext1', 'foo/bar/corge.ext1'))

    def test_files(self):
        ''' Files mapper should discard directories '''
        files, src = _file_mapper()
        src.glob('foo', 'qux.ext1').files()
        self._check_files(files(), ('qux.ext1', 'qux.ext1'))

    def test_glob_absolute(self):
        ''' Call to a file_mapper should support absolute paths '''
        abs_qux_path = os.path.abspath("mocks/file_mapper_tests/qux.ext1")
        files = nimp.system.FileMapper(mapper=_yield_mapper)
        files.to('.').glob(abs_qux_path)
        self.assertListEqual(list(files()), [(abs_qux_path, abs_qux_path)])

    def test_glob_recursive(self):
        ''' Call to a file_mapper should recursive globs '''
        files, src = _file_mapper()
        src.glob("**/*")
        self._check_files(files(), ('foo', 'foo'),
                          ('foo/bar', 'foo/bar'),
                          ('foo/bar/corge.ext1', 'foo/bar/corge.ext1'),
                          ('foo/bar/corge.ext2', 'foo/bar/corge.ext2'),
                          ('foo/quux.ext1', 'foo/quux.ext1'),
                          ('qux.ext1', 'qux.ext1'))

    def test_glob_src(self):
        ''' Glob src should be handled '''
        files, src = _file_mapper()
        src.src('fo*').glob('quux.ext1')
        self._check_files(files(), ('foo/quux.ext1', 'quux.ext1'))

    def test_once(self):
        ''' Multiple calls to the same once mapper shouldn't append
            already processed files '''
        mapper, src = _file_mapper()
        src.once().glob('qux.ext1')
        files = itertools.chain(mapper(), mapper())
        self._check_files(files, ('qux.ext1', 'qux.ext1'))

    def test_recursive(self):
        ''' Recursive mapper should include all childrens of an added
            directory. '''
        files, src = _file_mapper()
        src.glob('foo').recursive()
        self._check_files(files(), ('foo', 'foo'),
                          ('foo/bar', 'foo/bar'),
                          ('foo/bar/corge.ext1', 'foo/bar/corge.ext1'),
                          ('foo/bar/corge.ext2', 'foo/bar/corge.ext2'),
                          ('foo/quux.ext1', 'foo/quux.ext1'))

    def test_replace(self):
        ''' Replace should handle regular exression and replace them in destination path.'''
        files, src = _file_mapper(qux='qux.ext1', repl='foobar')
        src.glob('{qux}').replace('{qux}', '{repl}')
        self._check_files(files(), ('qux.ext1', 'foobar'))

    def test_src(self):
        ''' src is used in every test, just testing format here. '''
        files, src = _file_mapper(dir='foo')
        src.src('{dir}').glob('quux.ext1')
        self._check_files(files(), ('foo/quux.ext1', 'quux.ext1'))

    def test_src_dst(self):
        ''' src is used in every test, just testing format here. '''
        files, src = _file_mapper()
        src.src('foo').to('dest').glob('quux.ext1')
        self._check_files(files(), ('foo/quux.ext1', 'dest/quux.ext1'))
