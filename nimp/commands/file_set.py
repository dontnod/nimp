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

        parser.add_argument('--frm',
                            help    = 'Source directory',
                            metavar = '<DIR>')

        return True

    #---------------------------------------------------------------------------
    def run(self, context):
        for key_value in context.arg:
            setattr(context, key_value[0], key_value[1])
        context.standardize_names()
        load_ue3_context(context)
        map_files = None
        if context.action == 'robocopy':
            map_files = robocopy(context)
        elif context.action == 'checkout':
            map_files = checkout(context)
        elif context.action == 'list':
            def _list_mapper(source, destination, *args):
                log_notification("{0} => {1}", source, destination)
                yield True
            map_files = FileMapper(_list_mapper, format_args = vars(context))
        elif context.action == 'generate-toc':
            log_error("Not implemented yet")

        if context.frm is not None:
            map_files = map_files.frm(context.frm)

        if context.to is not None:
            map_files = map_files.to(context.to)

        return all(map_files.load_set(context.set_name))