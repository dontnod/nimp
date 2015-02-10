# -*- coding: utf-8 -*-

#---------------------------------------------------------------------------
def ue3_publish_binaries(publisher):
    publisher.delete_destination()
    platform      = publisher.platform
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
            publisher.add("Binaries\\{platform}\\", ['{game}*-*.*'], ['*.pdb', '*.map', '*.lib'])
        else:
            publisher.add("Binaries\\{platform}\\", ['{game}-{platform}-{configuration}.*'], ['*.pdb', '*.map', '*.lib'])

    return True

#---------------------------------------------------------------------------
def ue3_publish_version(publisher):
    if not ue3_publish_binaries(publisher):
        return False

    if publisher.platform.lower() == 'win64':
        publisher.add("{game}\\Script\\", ['*.*'])
        publisher.add("{game}\\ScriptFinalRelease\\", ['*.*'])

    return True

#---------------------------------------------------------------------------
def ue3_publish_cook(publisher):
    cook_platform = publisher.platform

    if platform.lower() == 'win64':
        platform = 'PC'
    if platform.lower() == 'win32':
        platform = 'PCConsole'

    suffix = 'Final' if (publisher.configuration in ['test', 'final'] and publisher.dlc is None) else ''

    if dlc is None:
        cook_directory = '{game}\\' + 'Cooked{0}{1}'.format(cook_platform, suffix)
    else:
        cook_directory = '{game}\\DLC\\{platform}\\{dlc}\\' + 'Cooked{0}{1}'.format(cook_platform, suffix)

    publisher.add(cook_directory)

    return True
