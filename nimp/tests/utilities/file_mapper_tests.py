# -*- coding: utf-8 -*-

import unittest
import os
import itertools
import tempfile

from nimp.utilities.file_mapper import *

def _yield_mapper(src, destination, *args):
    yield src, destination

class FileSetTests(unittest.TestCase):
    def __init__(self, methodName = 'runTest'):
        super(FileSetTests, self).__init__(methodName)

    def _file_mapper(self, **format_args):
        return FileMapper(_yield_mapper, format_args = format_args).frm("mocks/file_mapper_tests")

    def _check_files(self, mapper_files, *expected_files):
        abs_expected_files = []
        for file in expected_files:
            expected_src = os.path.normpath(os.path.join("mocks/file_mapper_tests", file[0]))
            abs_expected_files.append((expected_src, os.path.normpath(file[1])))
        self.assertListEqual(list(mapper_files), abs_expected_files)

    def test_map_sources(self):
        """ Calling a file mapper with a simple file name should process it."""
        files = map_sources(lambda src:src).frm("mocks/file_mapper_tests")('qux.ext1')
        self.assertListEqual(list(files), [os.path.normpath("mocks/file_mapper_tests/qux.ext1")])

    def test_call(self):
        """ Calling a file mapper with a simple file name should process it."""
        files = self._file_mapper(qux = 'qux.ext1')('{qux}')
        self._check_files(files, ('qux.ext1', 'qux.ext1'))

    def test_empty_call(self):
        """ Calling a file mapper with no argument should process empty path."""
        files = self._file_mapper()()
        self._check_files(files, ('', ''))

    def test_exclude(self):
        """ Exclude should remove files matching one of the given patterns.  """
        files = self._file_mapper().exclude('*.ext2')('foo/bar/corge.ext1',
                                                      'foo/bar/corge.ext2')
        self._check_files(files, ('foo/bar/corge.ext1', 'foo/bar/corge.ext1'))

    def test_files(self):
        """ Files mapper should discard directories """
        files = self._file_mapper().files()('foo', 'qux.ext1')
        self._check_files(files, ('qux.ext1', 'qux.ext1'))

    def test_from(self):
        """ From is used in every test, just testing format here. """
        files = self._file_mapper(dir = 'foo').frm('{dir}')('quux.ext1')
        self._check_files(files, ('foo/quux.ext1', 'quux.ext1'))

    def test_from_to(self):
        """ From is used in every test, just testing format here. """
        files = self._file_mapper().frm('foo').to('dest')('quux.ext1')
        self._check_files(files, ('foo/quux.ext1', 'dest/quux.ext1'))

    def test_glob_absolute(self):
        """ Call to a file_mapper should support absolute paths """
        abs_qux_path = os.path.abspath("mocks/file_mapper_tests/qux.ext1")
        files = FileMapper(_yield_mapper)(abs_qux_path)
        self.assertListEqual(list(files), [(abs_qux_path,abs_qux_path)])

    def test_glob_recursive(self):
        """ Call to a file_mapper should recursive globs """
        files = self._file_mapper()("**/*")
        self._check_files(files, ('foo', 'foo'),
                                 ('qux.ext1', 'qux.ext1'),
                                 ('foo/bar', 'foo/bar'),
                                 ('foo/quux.ext1', 'foo/quux.ext1'),
                                 ('foo/bar/corge.ext1', 'foo/bar/corge.ext1'),
                                 ('foo/bar/corge.ext2', 'foo/bar/corge.ext2'))

    def test_glob_from(self):
        """ Glob from could be used in the frm argument"""
        files = self._file_mapper().frm('fo*')('quux.ext1')
        self._check_files(files, ('foo/quux.ext1', 'quux.ext1'))

    def test_once(self):
        """ Multiple calls to the same once mapper shouldn't append
            already processed files """
        mapper = self._file_mapper().once()
        files = itertools.chain(mapper('qux.ext1'), mapper('qux.ext1'))
        self._check_files(files, ('qux.ext1', 'qux.ext1'))

    def test_recursive(self):
        """ Recursive mapper should include all childrens of an added
            directory. """
        files = self._file_mapper().recursive()('foo')
        self._check_files(files, ('foo', 'foo'),
                                 ('foo/bar', 'foo/bar'),
                                 ('foo/bar/corge.ext1', 'foo/bar/corge.ext1'),
                                 ('foo/bar/corge.ext2', 'foo/bar/corge.ext2'),
                                 ('foo/quux.ext1', 'foo/quux.ext1'))

    def test_to(self):
        """ To should translate target directory """
        files = self._file_mapper(dir = 'dest').to("{dir}")('qux.ext1')
        self._check_files(files, ('qux.ext1', 'dest/qux.ext1'))
