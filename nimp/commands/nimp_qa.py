# -*- coding: utf-8 -*-

import unittest

import nimp.tests.utilities.file_mapper_tests

from nimp.commands._command import *

#-------------------------------------------------------------------------------
class NimpQaCommand(Command):
    #---------------------------------------------------------------------------
    def __init__(self):
        Command.__init__(self, 'nimp-qa', 'Runs pylint on nimp and runs his unit tests')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        return unittest.main(module = nimp.tests.utilities.file_mapper_tests, argv = ["."])
