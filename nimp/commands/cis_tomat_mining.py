# -*- coding: utf-8 -*-

from nimp.commands._cis_command import *
from nimp.utilities.ue3         import *
from nimp.utilities.deployment  import *
from nimp.utilities.file_mapper import *

import tempfile
import shutil

#-------------------------------------------------------------------------------
class CisTomatMining(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self,
                            'cis-tomat-mining',
                            'Mines UE3 content into Tomat')

    #---------------------------------------------------------------------------
    def cis_configure_arguments(self, env, parser):
        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, env):

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

        if env.is_ue3:
            if success:
                success = ue3_commandlet(env.game, 'dnetomatminingcommandlet', [ tmpdir ])

            if success:
                success = call_process('.', [ 'TomatConsole',
                                              'ImportFromUnreal',
                                              '--RepositoryUri', 'sql://mining@console',
                                              '--TmpDirectory', tmpdir ]) == 0

        # Clean up after ourselves
        #shutil.rmtree(tmpdir)

        return success

