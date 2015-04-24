# -*- coding: utf-8 -*-

import argparse
import copy

#-------------------------------------------------------------------------------
class Command:
    #---------------------------------------------------------------------------
    def __init__(self,
                 name,
                 help,
                 dependencies = []):
        self._name          = name
        self._help          = help
        self._dependencies  = dependencies

    #---------------------------------------------------------------------------
    def name(self):
        return self._name

    #---------------------------------------------------------------------------
    def help(self):
        return self._help

    #---------------------------------------------------------------------------
    def dependencies(self):
        return self._dependencies

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        assert(False)

    #---------------------------------------------------------------------------
    def check(self, env):
        return True

    #---------------------------------------------------------------------------
    def _run_sub_command(self, env, command, arguments = []):
        new_context     = copy.copy(env)
        parser          = argparse.ArgumentParser()

        command.configure_arguments(env, parser)

        (parsed_arguments, unknown_args)   = parser.parse_known_args(arguments)

        setattr(new_context, 'arguments', parsed_arguments)
        setattr(parsed_arguments, "unknown_args", unknown_args)
        return command.run(new_context)

