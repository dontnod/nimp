# -*- coding: utf-8 -*-

from nimp.commands._command     import *
from nimp.utilities.ue3         import *
from nimp.utilities.file_mapper import *

#-------------------------------------------------------------------------------
class MapCommand(Command):
    def __init__(self):
        Command.__init__(self, 'file-set', 'Do stuff on a list of file (previously known as cookersync)')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        parser.add_argument('--arg',
                            help    = 'Set a format argument, that will be used in string interpolation.',
                            nargs=2,
                            action='append')

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
    def run(self, context):
        for key_value in context.arg:
            setattr(context, key_value[0], key_value[1])
        context.standardize_names()

        files       = FileMapper(format_args = vars(context))
        files_chain = files
        if context.src is not None:
            files_chain = files_chain.src(context.src)

        if context.to is not None:
            files_chain = files_chain.to(context.to)

        files_chain.load_set(context.set_name)

        if context.action == 'robocopy':
            map(robocopy(context), files)
        elif context.action == 'checkout':
            with p4_transaction('Checkout') as trans:
                map(trans.add, files)
        elif context.action == 'list':
            for source, destination in files():
                log_notification("{0} => {1}", source, destination)
        elif context.action == 'generate-toc':
            log_error("Not implemented yet")

        return True