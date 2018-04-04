# Copyright © 2018 Dontnod Entertainment
''' Command to execute a hook on its own '''


import nimp.command
import nimp.sys.process


class RunHook(nimp.command.Command):
    ''' Execute a hook on its own '''


    def __init__(self):
        super(RunHook, self).__init__()


    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'free_parameters')
        parser.add_argument('hook', metavar = '<hook>', help = 'Select the hook to execute')
        return True


    def is_available(self, env):
        return True, ''


    def run(self, env):
        return nimp.environment.execute_hook(env.hook, env)
