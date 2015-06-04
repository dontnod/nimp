# -*- coding: utf-8 -*-

from nimp.commands._command     import *
from nimp.utilities.ue3         import *
from nimp.utilities.file_mapper import *

#-------------------------------------------------------------------------------
class MapCommand(Command):
    def __init__(self):
        Command.__init__(self, 'file-set', 'Do stuff on a list of file (previously known as cookersync)')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('--arg',
                            help    = 'Set a format argument, that will be used in string interpolation.',
                            nargs=2,
                            action='append',
                            default = [])

        parser.add_argument('set_name',
                            help    = 'Set name to load',
                            metavar = '<SET_FILE>')

        parser.add_argument('action',
                            help    = 'Action to execute on listed files',
                            metavar = '<ACTION>',
                            choices = ['robocopy', 'checkout', 'generate-toc', 'list'])

        parser.add_argument('--to',
                            help    = 'Destination, if relevant',
                            metavar = '<DIR>',
                            default = None)

        parser.add_argument('--src',
                            help    = 'Source directory',
                            metavar = '<DIR>')

        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        if(env.arg is not None):
            for key_value in env.arg:
                setattr(env, key_value[0], key_value[1])
        env.standardize_names()

        files = FileMapper(format_args = vars(env))
        files_chain = files
        if env.src is not None:
            files_chain = files_chain.src(env.src)

        if env.to is not None:
            files_chain = files_chain.to(env.to)

        files_chain.load_set(env.set_name)

        if env.action == 'robocopy':
            for source, destination in files():
                robocopy(source, destination)
        elif env.action == 'checkout':
            with p4_transaction('Checkout') as trans:
                map(trans.add, files)
        elif env.action == 'list':
            for source, destination in files():
                log_notification("{0} => {1}", source, destination)
        elif env.action == 'generate-toc':
            log_error(log_prefix() + "Not implemented yet")

        return True
