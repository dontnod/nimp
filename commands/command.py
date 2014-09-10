# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
import argparse

#-------------------------------------------------------------------------------
# Command
#-------------------------------------------------------------------------------
class Command:
    #---------------------------------------------------------------------------
    # __init__
    def __init__(self,
                 name,
                 help,
                 dependencies = []):
        self._name          = name
        self._help          = help
        self._dependencies  = dependencies

    #---------------------------------------------------------------------------
    # name
    def name(self):
        return self._name

    #---------------------------------------------------------------------------
    # help
    def help(self):
        return self._help

    #---------------------------------------------------------------------------
    # dependencies
    def dependencies(self):
        return self._dependencies

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):
        return True

    #---------------------------------------------------------------------------
    # run
    def run(self, context):
        assert(False)

    #---------------------------------------------------------------------------
    # check
    def check(self, context):
        return True

    #---------------------------------------------------------------------------
    # _run_sub_command
    def _run_sub_command(self, context, command, additional_arguments = []):
        arguments       = context.arguments
        parser          = argparse.ArgumentParser()
        all_args        = arguments.unknown_args + additional_arguments

        command.configure_arguments(context, parser)
        parser.set_defaults(**arguments.__dict__)

        (command_arguments, unknown_args)   = parser.parse_known_args(all_args)
        arguments_dictionary                = command_arguments.__dict__

        for (key, value) in arguments_dictionary.items():
            setattr(arguments, key, value)

        setattr(arguments, "unknown_args", unknown_args)
        return command.run(context)

