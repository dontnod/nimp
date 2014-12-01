# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# imports
#-------------------------------------------------------------------------------
import commands

from commands.command           import *
from modules.module             import *

from utilities.inspection       import *
from utilities.logging          import *

#-------------------------------------------------------------------------------
# Commands
#-------------------------------------------------------------------------------
class CommandsModule(Module):
    #---------------------------------------------------------------------------
    # __init__
    def __init__(self):
        Module.__init__(self, "commands", ["configuration", "logging"])
        self._commands = get_instances(commands, Command)

    #---------------------------------------------------------------------------
    # configure_arguments
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
    # load
    def load(self, context):
        command_to_run       = context.arguments.command_to_run
        return command_to_run.run(context)

