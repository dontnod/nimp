# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
from datetime import date

from commands.command       import *

from utilities.files        import *
from utilities.hashing      import *
from utilities.paths        import *
from utilities.processes    import *

#-------------------------------------------------------------------------------
# Ue3LooseFilesCommand
#-------------------------------------------------------------------------------
class Ue3LooseFilesCommand(Command):

    def __init__(self):
        Command.__init__(self, "ue3-loose", "Generate loose files")

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('game',
                            metavar = '<game>',
                            type    = str)

        parser.add_argument('platform',
                            help    = 'Generate loose files for this platform',
                            metavar = '<platform>',
                            default = settings.default_ue3_platforms)

        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configurations to cook',
                            metavar = '<configuration>',
                            nargs   = '+',
                            default = settings.default_ue3_configurations)


        parser.add_argument('-l',
                            '--lang',
                            help    = 'languages to cook',
                            metavar = '<lang>',
                            nargs   = '+',
                            default = "INT")
        return True

    #---------------------------------------------------------------------------
    # run
    def run(self, context):
        settings                    = context.settings
        arguments                   = context.arguments
        current_workspaces          = p4_get_workspaces_containing_path(".")
        shipping_directory_template = settings.shipping_directory_template
        cookersync_tagset           = shipping_cookersync_tagset
        cookersync_path             = cookersync_path

        if len(current_workspaces) == 0:
            log_error("Unable to find current workspace, can't determine last synced changelist")
            return False

        changelist  = p4_get_last_synced_changelist(current_workspaces[0])

        shipping_directory   = shipping_directory_template.format(platform   = arguments.platform,
                                                                  changelist = changelist,
                                                                  build_type = 'test')
        today               = date.today()
        shipping_directory  = today.strftime(shipping_directory)

        cookersync_commandline = [cookersync_path, settings.game, "-p", arguments.platform, "-x", cookersync_tagset, "-b", shipping_directory]
        for language in arguments.lang:
            cookersync_commandline += ["-r", language]

        cookersync_commandline += ["NullDingo"]

        if not call_process('.', cookersync_commandline):
            return False

        return True