# -*- coding: utf-8 -*-

from nimp.utilities.deployment import *
from nimp.utilities.file_mapper import *
from nimp.utilities.ue3        import *


#---------------------------------------------------------------------------
def ue3_map_binaries(publish):
    configuration       = publish.configuration
    publish_binaries    = publish.frm("Binaries").to("Binaries").exclude("*.pdb", "*.map", "*.lib")

    if (publish.is_win64 or publish.is_win32):
        if configuration == 'Release' or configuration is None:
            yield publish_binaries("{ue3_build_platform}\\{game}.exe",
                                   "{ue3_build_platform}\\{game}.exe.config",
                                   "{ue3_build_platform}\\{game}.config",
                                   "{ue3_build_platform}\\{game}.com",
                                   "{ue3_build_platform}\\AgentInterface.dll",
                                   "Xbox360\\Interop.XDevkit.1.0.dll",
                                   "PS3\\PS3Tools_x64.dll",
                                   "Xbox360\\Xbox360Tools_x64.dll",
                                   "Orbis\\OrbisTools_x64.dll",
                                   "Dingo\\DingoTools_x64.dll",
                                   "Win64\\Microsoft.VC90.CRT\\*.*",
                                   "{ue3_build_platform}\\*.dll'",
                                   '*.xml', '*.bat', '*.dll', '*.exe.config', '*.exe',
                                   "Win64\\Editor\\Release\\*.*",
                                   "{ue3_build_platform}\\{game}.*")

        if configuration != 'Release':
            yield publish_binaries("{ue3_build_platform}\\{game}-{ue3_build_platform}-{configuration}.*")

    if (not publish.is_win64 and not publish.is_win32):
        if configuration is None:
            yield publish_binaries("{ue3_build_platform}\\{game}*-*.*")
        else:
            yield publish_binaries("{ue3_build_platform}\\{game}-{ue3_build_platform}-{configuration}.*")


#---------------------------------------------------------------------------
def ue3_map_version(publish):
    for configuration in publish.configurations:
        for result in ue3_map_binaries(publish.override(configuration = configuration)):
            yield result

    if publish.is_win64:
        yield publish("{game}\\Script\\*.*", "{game}\\ScriptFinalRelease\\*.*")

    return True

#---------------------------------------------------------------------------
def ue3_map_patch(patch):
    return chain(patch.patch_files(patch))

#---------------------------------------------------------------------------
def ue3_map_dlc(patch):
    return chain(patch.dlc_files(patch))

