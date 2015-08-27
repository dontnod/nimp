# -*- coding: utf-8 -*-

from nimp.commands._command import *

from nimp.utilities.ue3         import *
from nimp.utilities.deployment  import *
from nimp.utilities.file_mapper import *

import tempfile
import shutil

#-------------------------------------------------------------------------------
class TomatMining(Command):

    def __init__(self):
        Command.__init__(self, 'tomat-mining', 'Mines UE3 content into Tomat')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        return True

    #---------------------------------------------------------------------------
    def run(self, env):

        # Must be a UE3 project
        if not env.is_ue3:
            log_error(log_prefix() + "Invalid project type {0}" % (env.project_type))
            return False

        # Install tomat-console using pacman
        if call_process('.', ['pacman', '-S', '--noconfirm', 'repman']) != 0:
            return False

        if call_process('.', ['repman', 'add', 'dont-nod', 'http://pacman/']) != 0:
            return False

        if call_process('.', ['pacman', '-Scc', '--noconfirm']) != 0:
            return False

        if call_process('.', ['pacman', '-S', '--noconfirm', '--force', 'tomat-console']) != 0:
            return False

        tmpdir = tempfile.mkdtemp()
        success = True

        if success:
            success = ue3_commandlet(env.game, 'dnetomatminingcommandlet', [ tmpdir ])

        if success:
            success = call_process('.', [ 'TomatConsole',
                                          'ImportFromUnreal',
                                          '--RepositoryUri', 'sql://mining@console',
                                          '--TmpDirectory', tmpdir ]) == 0
        # Clean up after ourselves
        shutil.rmtree(tmpdir)

        return success

