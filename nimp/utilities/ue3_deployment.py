# -*- coding: utf-8 -*-

from nimp.utilities.deployment import *
from nimp.utilities.ue3        import *

#-------------------------------------------------------------------------------
def get_cook_platform_name(platform_name):
    platform_names = {
        "ps4"       : "Orbis",
        "xboxone"   : "Dingo",
        "win64"     : "PC",
        "win32"     : "PCConsole",
        "xbox360"   : "Xbox360",
        "ps3"       : "PS3" }

    platform_name = platform_name.lower()

    if not platform_name in platform_names:
        return platform_name

    return platform_names[platform_name]

#-------------------------------------------------------------------------------
def get_binaries_platform(platform):
    platforms = {
        "ps4"       : "Orbis",
        "xboxone"   : "Dingo",
        "win64"     : "Win64",
        "win32"     : "Win32",
        "xbox360"   : "Xbox360",
        "ps3"       : "PS3" }

    platform = platform.lower()

    if not platform in platforms:
        return platform

    return platforms[platform]

#-------------------------------------------------------------------------------
def get_cook_directory(game, project, dlc, platform, configuration):
    cook_platform = get_cook_platform_name(platform)

    suffix = 'Final' if (configuration.lower() in ['test', 'final'] and dlc == project) else ''

    if dlc == project:
        return '{0}\\Cooked{1}{2}'.format(game, cook_platform, suffix)
    else:
       return '{0}\\DLC\\{platform}\\{dlc}\\Cooked{1}{2}'.format(game, cook_platform, suffix)

#---------------------------------------------------------------------------
def ue3_publish_binaries(publisher):
    platform      = get_binaries_platform(publisher.platform)
    configuration = publisher.configuration

    if (platform == 'Win32' or platform == 'Win64'):
        if configuration == 'Release' or configuration is None:
            publisher.add("Binaries\\{platform}\\{game}.exe")
            publisher.add("Binaries\\{platform}\\{game}.exe.config")
            publisher.add("Binaries\\{platform}\\{game}.config")
            publisher.add("Binaries\\{platform}\\{game}.com")
            publisher.add("Binaries\\Xbox360\\Interop.XDevkit.1.0.dll")
            publisher.add("Binaries\\PS3\\PS3Tools_x64.dll")
            publisher.add("Binaries\\Xbox360\\Xbox360Tools_x64.dll")
            publisher.add("Binaries\\Orbis\\OrbisTools_x64.dll")
            publisher.add("Binaries\\Dingo\\DingoTools_x64.dll")

            publisher.add("Binaries\\Win64\\Microsoft.VC90.CRT", ['*.*'])
            publisher.add("Binaries\\{platform}", ['*.dll'], recursive = False )
            publisher.add("Binaries\\", ['*.xml', '*.bat', '*.dll', '*.exe.config', '*.exe'], recursive = False)
            publisher.add("Binaries\\Win64\\Editor\\Release", ['*.*'], recursive = False)
            publisher.add("Binaries\\{platform}", ['{game}.*'], ['*.pdb', '*.map', '*.lib'], recursive = False)

        if configuration != 'Release':
            publisher.add("Binaries\\{platform}\\", ['{game}-{platform}-{configuration}.*'], ['*.pdb', '*.map', '*.lib'])

    if (platform != 'Win32' and platform != 'Win64'):
        if configuration is None:
            publisher.add("Binaries\\{platform}\\", ['{game}*-*.*'], ['*.lib'])
        else:
            publisher.add("Binaries\\{platform}\\", ['{game}-{platform}-{configuration}.*'], ['*.lib'])

    return True

#---------------------------------------------------------------------------
def ue3_publish_version(publisher):
    for configuration in publisher.configurations:
        if not publish(publisher,
                       ue3_publish_binaries,
                       publisher.destination,
                       platform      = get_binaries_platform(publisher.platform),
                       configuration = configuration):
            return False

    if publisher.platform.lower() == 'win64':
        publisher.add("{game}\\Script\\", ['*.*'])
        publisher.add("{game}\\ScriptFinalRelease\\", ['*.*'])

    return True

#---------------------------------------------------------------------------
def ue3_publish_patch(publisher):
    cook_directory  = get_cook_directory(publisher.game, publisher.project, publisher.dlc, publisher.platform, 'final')
    patched_files   = list(publisher.patched_files(publisher, cook_directory))
    for file in patched_files:
        publisher.add(file)
    return True

#---------------------------------------------------------------------------
def ue3_publish_cook(publisher):
    cook_directory = get_cook_directory(publisher.project, publisher.dlc, publisher.platform, 'final')
    publisher.add(cook_directory)

    return True