# -*- coding: utf-8 -*-

import nimp.commands

from nimp.commands._command    import *
from nimp.modules.module       import *
from nimp.utilities.inspection import *
from nimp.utilities.logging    import *

#-------------------------------------------------------------------------------
class CommandsModule(Module):
    #---------------------------------------------------------------------------
    def __init__(self):
        Module.__init__(self, "commands", ["configuration", "logging"])
        self._commands = get_instances(nimp.commands, Command)

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        subparsers  = parser.add_subparsers(title='Commands')
        for command_it in self._commands:
            command_parser = subparsers.add_parser(command_it.name(),
                                                   help = command_it.help())
            if not command_it.configure_arguments(context, command_parser):
                return False
            command_parser.set_defaults(command_to_run = command_it)
        return True

    #---------------------------------------------------------------------------
    def load(self, context):
        command_to_run       = context.command_to_run
        return command_to_run.run(context)

