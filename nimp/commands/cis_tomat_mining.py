# -*- coding: utf-8 -*-

from nimp.commands._cis_command import *
from nimp.utilities.ue3         import *
from nimp.utilities.deployment  import *
from nimp.utilities.file_mapper import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

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

        if call_process('.', ['repman', 'add', 'dont-nod', 'http://pacman']) != 0:
            return False

        if call_process('.', ['pacman', '-S', '--noconfirm', '--needed', 'tomat-console']) != 0:
            return False

        return call_process('.',
                            [ 'TomatConsole',
                              'ImportFromUnreal',
                              '--RepositoryUri',
                              'sql://mining@console',
                              '--UnrealEnginePath',
                              'Binaries/Win64/ExampleGame.exe' ])
