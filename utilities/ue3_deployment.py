# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
import socket
import random
import string
import time
import contextlib
import shutil

from utilities.build        import *
from utilities.deployment   import *

#---------------------------------------------------------------------------
def ue3_publish_binaries(destination_format, project, game, revision, platform, configuration = None):
    if platform.lower() == "XboxOne":
        platform = "Dingo"

    elif platform.lower() == "PS4":
        platform = "Orbis"

    publisher = FilePublisher(destination_format, project, game, platform, configuration, dlc = None, language = None, revision = revision)
    publisher.delete_destination()

    if (platform == 'Win32' or platform == 'Win64') and (configuration == 'Release' or configuration is None):
        publisher.add("Binaries\\{platform}\\{game}.exe")
        publisher.add("Binaries\\{platform}\\{game}.exe.config")
        publisher.add("Binaries\\{platform}\\{game}.config")
        publisher.add("Binaries\\{platform}\\{game}.com")
        publisher.add("Binaries\\Xbox360\\Interop.XDevkit.1.0.dll")
        publisher.add("Binaries\\PS3\\PS3Tools_x64.dll")
        publisher.add("Binaries\\Xbox360\\Xbox360Tools_x64.dll")
        publisher.add("Binaries\\Orbis\\OrbisTools_x64.dll")
        publisher.add("Binaries\\Dingo\\DingoTools_x64.dll")

        publisher.add("Binaries\\Win64\\Microsoft.VC90.CRT",    ['*.*'])
        publisher.add("Binaries\\{platform}",                   ['*.dll'], recursive = False )
        publisher.add("Binaries\\",                             ['*.xml', '*.bat', '*.dll', '*.exe.config', '*.exe'], recursive = False)
        publisher.add("Binaries\\Win64\\Editor\\Release",       ['*.*'], recursive = False)

    if configuration == 'Release':
        publisher.add("Binaries\\{platform}", ['{game}.*'], ['*.pdb', '*.map', '*.lib'], recursive = False)

    if configuration is not None and configuration != 'Release':
        publisher.add("Binaries\\{platform}\\", ['{game}-{platform}-{configuration}.*'], ['*.pdb', '*.map', '*.lib'])

    if configuration is None:
        publisher.add("Binaries\\{platform}\\", ['{game}*-*.*', '{game}.*'], ['*.pdb', '*.map', '*.lib'])

    return True

#---------------------------------------------------------------------------
def ue3_publish_version(destination_format, project, game, revision, platform):
    if not ue3_publish_binaries(destination_format, project, game, revision, platform, None):
        return False

    publisher = FilePublisher(destination_format, project, game, platform, configuration = None, dlc = None, language = None, revision = revision)
    publisher.add("{game}\\Script\\", ['*.*'])
    publisher.add("{game}\\ScriptFinalRelease\\", ['*.*'])

    return True

#---------------------------------------------------------------------------
def ue3_publish_cook(destination_format, project, game, platform, configuration, revision):
    publisher = FilePublisher(destination_format, project, game, platform, configuration = configuration, revision = revision)

    return True
