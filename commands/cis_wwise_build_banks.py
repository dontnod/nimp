# -*- coding: utf-8 -*-
from commands._cis_command  import *
from utilities.wwise        import *

#-------------------------------------------------------------------------------
class BuildWwiseBanksCommand(CisCommand):
    abstract = 0
    #---------------------------------------------------------------------------
    def __init__(self):
        CisCommand.__init__(self, 'cis-wwise-build-banks', 'Builds Wwise Banks')

    #---------------------------------------------------------------------------
    def cis_configure_arguments(self, context, parser):
        parser.add_argument('platform',
                            help    = 'Platform to build',
                            metavar = '<PLATFORM>')

        parser.add_argument('--checkin',
                            help    = 'Automatically checkin result',
                            action  = "store_true",
                            default = False)
        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, context):
        return build_wwise_banks(context.platform,
                                 context.wwise_banks_path,
                                 context.wwise_project,
                                 context.checkin)
