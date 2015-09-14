# -*- coding: utf-8 -*-

from nimp.commands._command     import *
from nimp.utilities.ue3         import *
from nimp.utilities.file_mapper import *

#-------------------------------------------------------------------------------
class MapCommand(Command):
    def __init__(self):
        Command.__init__(self, 'fileset', 'Do stuff on a list of files')

    #---------------------------------------------------------------------------
    def configure_arguments(self, env, parser):
        parser.add_argument('--arg',
                            help    = 'Add a key/value pair for use in string interpolation',
                            metavar = '<KEY>=<VALUE>',
                            nargs   = 1,
                            action  = 'append',
                            default = [])

        parser.add_argument('set_name',
                            help    = 'Set name to load (e.g. binaries, version…)',
                            metavar = '<SET_FILE>')

        parser.add_argument('action',
                            help    = 'Action to execute on listed files (one of: robocopy, checkout, toc, reconcile, reconcile_and_submit, list)',
                            metavar = '<ACTION>',
                            choices = ['robocopy', 'checkout', 'toc', 'reconcile', 'reconcile_and_submit', 'list'])

        parser.add_argument('--src',
                            help    = 'Source directory',
                            metavar = '<DIR>')

        parser.add_argument('--to',
                            help    = 'Destination, if relevant',
                            metavar = '<DIR>',
                            default = None)

        return True

    #---------------------------------------------------------------------------
    def run(self, env):
        if env.arg is not None:
            for key, value in [x[0].split('=') for x in env.arg]:
                setattr(env, key, value)
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
        elif env.action == 'toc':
            log_error("Not implemented yet")

        return True
