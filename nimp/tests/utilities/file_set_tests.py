# -*- coding: utf-8 -*-

import unittest
import os
import tempfile

from nimp.utilities.file_set import *

class FileSetTests(unittest.TestCase):
    def __init__(self, methodName = 'runTest'):
        super(FileSetTests, self).__init__(methodName)

    def setUp(self):
        self._test_directory = tempfile.mktemp()
        os.makedirs(self._test_directory)
        def touch(*args):
            fname = os.path.join(self._test_directory, *args)
            if os.path.exists(fname):
                os.utime(fname, None)
            else:
                open(fname, 'w').close()

        def mkdir(*args):
            dir = os.path.join(self._test_directory, *args)
            os.makedirs(dir)

        touch("file_100.ext1")
        mkdir("nested_100", "nested_110")
        touch("nested_100", "nested_110", "file_111.ext1")
        touch("nested_100", "nested_110", "file.test_ext")
        touch("nested_100", "file.test_ext")

    def tearDown(self):
        return super(FileSetTests, self).tearDown()

    def _file_list(self):
        class DummyContext:
            pass
        return list_files(DummyContext()).frm(self._test_directory)

    def _copy_list(self):
        class DummyContext:
            pass
        return copy_files(DummyContext()).frm(self._test_directory)

    def _check_files(self, files, *expected_files):
        norm_files = []
        for file in expected_files:
            file = os.path.join(self._test_directory, file)
            file = os.path.normpath(file)
            norm_files.append(file)
        files = list(files)
        files.sort()
        norm_files.sort()
        self.assertListEqual(files, norm_files)

    def _check_file_pairs(self, files, *expected_files):
        norm_files = []
        for source, destination in expected_files:
            source      = os.path.join(self._test_directory, source)
            source      = os.path.normpath(source)
            destination = os.path.normpath(destination)
            norm_files.append((source, destination))
        files = list(files)
        files.sort()
        norm_files.sort()
        self.assertListEqual(files, norm_files)

    def test_add(self):
        """ Adding a simple file should end with it being in the file set. """
        files = self._file_list().add("file_100.ext1")
        self._check_files(files, "file_100.ext1")

    def test_glob_add(self):
        """ Globs should work in the path given to add. """
        files = self._file_list().add("*/*/file_111.ext1")
        self._check_files(files, "nested_100/nested_110/file_111.ext1")

    def test_from(self):
        """ 'frm' decorator should change base directory of further calls to 'add'. """
        files = self._file_list().frm('nested_100/nested_110').add("*.ext1")
        self._check_files(files, "nested_100/nested_110/file_111.ext1")

    def test_glob_from(self):
        """ Globs should work in the 'frm' path. """
        files = self._file_list().frm('*/nested_110').add("file_111.ext1")
        self._check_files(files, "nested_100/nested_110/file_111.ext1")

    def test_format_from(self):
        """ Path given to frm should be expanded """
        format_args = { 'dir' : 'nested_100' }
        files = self._file_list().format(**format_args).frm("{dir}/*").add("*.ext1")
        self._check_files(files, "nested_100/nested_110/file_111.ext1")

    def test_format(self):
        """ A call to 'format' dictionnary should replace format string in every further calls to 'add' """
        format_args = { 'file_name' : 'file_100.ext1' }
        files = self._file_list().format(**format_args).add("{file_name}")
        self._check_files(files, "file_100.ext1")

    def test_override_format(self):
        """ If two susequent calls to format are made, the last one should override previous values """
        format_args_1 = {
            'file_name' : 'file_111.ext1',
            'dir'       : 'this_should_be_overwritten_by_format_args_2'
        }

        format_args_2 = {
            'dir'       : 'nested_100/nested_110'
        }

        files = self._file_list().format(**format_args_1).format(**format_args_2).add("{dir}/{file_name}")
        self._check_files(files, "nested_100/nested_110/file_111.ext1")

    def test_recursive(self):
        """ recursive decorator should add all files in directories matched by subsequent 'add' calls """
        files = self._file_list().recursive().add("*")
        self._check_files(files,
                          "file_100.ext1",
                          "nested_100/nested_110/file_111.ext1",
                          "nested_100/nested_110/file.test_ext",
                          "nested_100/file.test_ext")

    def test_exclude(self):
        """ Exclude should exclude all files added by subsequent 'add' calls """
        files = self._file_list().exclude("*.test_ext").recursive().add("*")
        self._check_files(files,
                          "file_100.ext1",
                          "nested_100/nested_110/file_111.ext1")

    def test_to(self):
        """ To sould modify destination path of files matched by subsequent 'add' calls """
        files = self._copy_list().to("subdirectory").add("file_100.ext1")
        self._check_file_pairs(files, ("file_100.ext1", "subdirectory/file_100.ext1"))

    def test_format_to(self):
        """ Path given to 'to' should be expanded """
        format_args = { 'dir' : 'target' }
        files = self._copy_list().format(**format_args).to("{dir}").add("nested_100/nested_110/file_111.ext1")
        self._check_file_pairs(files, ("nested_100/nested_110/file_111.ext1", "target/nested_100/nested_110/file_111.ext1"))

    def test_glob_from_to(self):
        """ Globs 'frm' path should be handled and wiped from destination directory. """
        files = self._copy_list().frm("*/*").to("subdirectory").add("file_111.ext1")
        self._check_file_pairs(files, ("nested_100/nested_110/file_111.ext1", "subdirectory/file_111.ext1"))