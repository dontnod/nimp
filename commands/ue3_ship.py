# -*- coding: utf-8 -*-

from datetime import date
import tempfile
import shutil
import glob
import os

from commands.command       import *
from commands.ue3_cook      import *
from commands.ue3_build     import *

from utilities.perforce     import *
from utilities.files        import *
from utilities.hashing      import *
from utilities.paths        import *
from utilities.processes    import *

COOKERSYNC_PATH                = "Binaries/Cookersync.exe"
SHIPPED_LANGUAGES              = ['INT', 'FRA']
LOOSE_FILES_DIRECTORY_TEMPLATE = '\\\\build\\ship\\LIS-{platform}-%Y%m%d-{changelist}-{build_type}\\Loose\\{episode}';
PACKAGES_FILES_TEMPLATE        = '\\\\build\\ship\\LIS-{platform}-%Y%m%d-{changelist}-{build_type}\\Packages\\{episode}';
EPISODES                       = ["Episode01", "Episode02", "Episode03", "Episode04", "Episode05"]

#--------------------------------------------------------------------------------
class Ue3ShipCommand(Command):
    """Publishes a version in shipping directory"""

    def __init__(self):
        Command.__init__(self, "ue3-ship", "Ships the game")

    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('platform',
                            help    = 'Ship this platform',
                            metavar = '<platform>',
                            type    = str)

        parser.add_argument('configuration',
                            help    = 'Ship this configuration',
                            metavar = '<configuration>',
                            type    = str,
                            choices = ["test", "final"])

        parser.add_argument('-r',
                            '--revision',
                            help    = 'Revision',
                            metavar = '<revision>')

        parser.add_argument('-d',
                            '--dlc',
                            help    = 'Dlc to cook',
                            metavar = '<dlc_nqmd>',
                            default = None)
        return True

    #--------------------------------------------------------------------------
    def run(self, context):
        settings            = context.settings
        arguments           = context.arguments
        changelist          = arguments.changelist
        dlc                 = arguments.dlc

        return self._ship_episode(context, changelist, dlc, dlc is not None)

    #--------------------------------------------------------------------------
    def _ship_episode(self, context, changelist, episode, is_dlc):
        arguments           = context.arguments
        game                = settings.game
        platform            = arguments.platform
        configuration       = arguments.configuration

        loose_files_directory   = format_directory(LOOSE_FILES_DIRECTORY_TEMPLATE, platform, episode, changelist, configuration)
        packages_directory      = format_directory(PACKAGES_FILES_TEMPLATE, platform, episode, changelist, configuration)

        sync_loose_files(game, platform, episode, loose_files_directory)

        if platform.lower() == 'xboxone':
            generate_chunk(loose_files_directory)
            make_xvc(loose_files_directory, packages_directory)

        return True

#-------------------------------------------------------------------------------
def format_directory(template, platform, episode, changelist, build_type):
    """Formats a directory template with date and build arguments"""
    result = template.format(platform   = platform,
                             changelist = changelist,
                             episode    = episode,
                             build_type = 'test')
    today   = date.today()
    result  = today.strftime(result)
    return result

#-------------------------------------------------------------------------------
def sync_loose_files(game, platform, episode, target_directory):
    """Publishes loose files to given directory"""

    if os.path.exists(target_directory):
        shutil.rmtree(target_directory)

    for language in SHIPPED_LANGUAGES:
        call_cooker_sync(game, platform, "Loc", target_directory, episode, language)

    call_cooker_sync(game, platform, "DneShip", target_directory, episode, "INT")

    if episode is not "Episode01" and platform.lower() == 'xboxone':
        appmanifest_file = os.path.join("ExampleGame/Build/XboxOne/DLC", episode, "AppxManifest.xml")
        shutil.copyfile(appmanifest_file, target_directory)

#-------------------------------------------------------------------------------
def call_cooker_sync(game, platform, tagset, base_directory, episode, language):
    """Calls cookersync for a given tagset"""
    command_line_template = "{cookersync_path} {game} -a -p {platform} -x {tagset} -b {base_directory} -dlcname {episode} -r {language} -o -f -final NullDingo"
    commandline           = command_line_template.format(cookersync_path = COOKERSYNC_PATH,
                                                         game           = game,
                                                         platform       = platform,
                                                         tagset         = tagset,
                                                         episode        = episode,
                                                         base_directory = base_directory,
                                                         language       = language)
    return call_process('.', commandline)

#-------------------------------------------------------------------------------
def generate_chunk(directory):
    """Generates a XboxOne chunk file."""
    chunk_file_content = "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n\
<Package>\n\
  <Chunk Id=\"Registration\" Marker=\"Launch\">\n"

    for root, dirnames, filenames in os.walk(directory):
        for file in filenames:
            chunk_file_content += "  <FileGroup Include=\"{file}\" SourcePath=\"{root}\" DestinationPath=\"{root}\"/>\n".format(file = file,
                                                                                                                                root = os.path.relpath(root, directory))
    chunk_file_content += "  </Chunk>\n\
</Package>"
    chunk_path = os.path.join(directory, "chunk.xml")
    write_file_content(chunk_path, chunk_file_content)

#-------------------------------------------------------------------------------
def make_xvc(source_directory, target_directory):
    """Calls makepkg to build XVC"""
    temporary_directory = tempfile.mkdtemp()
    durango_xdk_folder  = os.environ['DURANGOXDK']
    make_pkg_path       = os.path.join(durango_xdk_folder, "bin", "makepkg.exe")

    call_process(".", [make_pkg_path, "pack", "/v", "/l", "/f", "{0}/chunk.xml".format(source_directory),  "/d", source_directory, "/pd", temporary_directory])

    if os.path.exists(target_directory):
        shutil.rmtree(target_directory, True)
    shutil.move(temporary_directory, target_directory)
