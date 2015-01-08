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

COOKERSYNC_PATH  = "Binaries/Cookersync.exe"

#-------------------------------------------------------------------------------
class Ue3PublishTagsetCommand(Command):

    def __init__(self):
        Command.__init__(self, "ue3-publish-tagset", "Publishes a zipped tagset to a shared repository")

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('game',
                            metavar = '<game>',
                            type    = str)

        parser.add_argument('tagset',
                            help    = 'Publish this tagset',
                            metavar = '<tagset>',
                            type    = str)

        parser.add_argument('destination',
                            help    = 'Publish destination',
                            metavar = '<destination>',
                            type    = str)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'Generate publish for this platform',
                            metavar = '<platform>',
                            type    = str)

        parser.add_argument('-l',
                            '--lang',
                            help    = 'Languages to publish',
                            metavar = '<lang>',
                            nargs   = '+',
                            default = ["INT", "FRA"])

        parser.add_argument('--dlcname',
                            help    = 'DLC to cook',
                            metavar = '<dlcname>')

        parser.add_argument('-g',
                            '--generic-var',
                            help    = 'Generic Key / Value pair configuration value to pass to CookerSync',
                            nargs   = 2,
                            action  ='append',
                            metavar = '<key> = <value>',
                            default = [])

        return True

    #---------------------------------------------------------------------------
    # run
    def run(self, context):
        settings        = context.settings
        arguments       = context.arguments
        command_line    = [COOKERSYNC_PATH, arguments.game,"-x", arguments.tagset, "-config-file", "DNE_CookerSync.xml", "-f", "-final", "-crc", "-l", "-b", "."]
        platform        = arguments.platform

        if platform is not None:
            if platform.lower() == 'win64':
                platform = 'PC'
            elif platform.lower() == 'win32':
                platform = 'PCConsole'
            command_line = command_line + [ "-p", platform ]

        for key, value in arguments.generic_var:
            command_line = command_line + ["-var", "{0}={1}".format(key, value)]

        for language in arguments.lang:
            command_line = command_line + ["-r", language]

        dlcname = arguments.dlcname
        if dlcname is not None:
            command_line = command_line + ["-dlcname", dlcname]

        command_line = command_line + [arguments.destination]

        return call_process(".", command_line)
