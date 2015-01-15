# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
from commands.cis_command       import *
from utilities.ue3              import *
from utilities.ue3_deployment   import *

FARM_P4_PORT     = "192.168.1.2:1666"
FARM_P4_USER     = "CIS-CodeBuilder"
FARM_P4_PASSWORD = "CIS-CodeBuilder"

#-------------------------------------------------------------------------------
class CisUe3Ship(CisCommand):
    abstract = 0
    def __init__(self):
        CisCommand.__init__(self, 'cis-ue3-ship', 'Cooks and publish a final version.')

    #---------------------------------------------------------------------------
    def configure_arguments(self, context, parser):
        CisCommand.configure_arguments(self, context, parser)
        settings = context.settings

        parser.add_argument('-r',
                            '--revision',
                            help    = 'Current revision',
                            metavar = '<revision>',
                            default = None)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to publish',
                            metavar = '<platform>')

        parser.add_argument('-c',
                            '--configuration',
                            help    = 'Configurations to publish',
                            metavar = '<platform>',
                            choices = ['test', 'final'])

        parser.add_argument('--dlc',
                            help    = 'Dlc to cook',
                            metavar = '<platform>',
                            default = None)
        return True

    #---------------------------------------------------------------------------
    def _cis_run(self, context):
        settings  = context.settings
        arguments = context.arguments

        project         = settings.project_name
        game            = settings.game
        languages       = settings.languages
        dlc             = arguments.dlc
        map             = settings.cook_maps[dlc or 'default']
        platform        = arguments.platform
        configuration   = arguments.configuration
        cook_directory  = settings.cis_cook_directory
        revision        = arguments.revision

        if not _deploy_revisions(context):
            return False

        if dlc is not None:
            if not deploy(settings.freezed_cook_directory,
                          project           = project,
                          game              = game,
                          platform          = platform,
                          configuration     = configuration,
                          revision          = revision):

                if not deploy(cook_directory,
                              project           = project,
                              game              = game,
                              platform          = platform,
                              configuration     = configuration,
                              revision          = revision):
                    return False

        if not ue3_cook(game, map, languages, dlc, platform, configuration):
            return False

        if dlc is None:
            if not ue3_publish_cook(cook_directory, project, game, platform, configuration, revision):
                return False

        return True

#-------------------------------------------------------------------------------
def _deploy_revisions(context):
    settings  = context.settings
    arguments = context.arguments
    revision  = arguments.revision or get_latest_available_revision(settings.cis_version_directory,
                                                                    platforms = ['Win64', arguments.platform],
                                                                    project   = settings.project_name,
                                                                    game      = settings.game)
    if not deploy(settings.cis_version_directory,
                  project  = settings.project_name,
                  game     = settings.game,
                  revision = revision,
                  platform = 'Win64'):
        return False

    if arguments.platform.lower() != 'win64':
        if not deploy(settings.cis_version_directory,
                      project  = settings.project_name,
                      game     = settings.game,
                      revision = revision,
                      platform = platform):
            return False

    return True



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
