# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
from commands.command       import *

from configuration.build    import *

from utilities.files        import *
from utilities.hashing      import *
from utilities.paths        import *
from utilities.processes    import *

if OS == WINDOWS:
    import _winreg
    from packages.visual_studio_tools_package   import *
    from utilities.windows_utilities            import *

#-------------------------------------------------------------------------------
# BuildCommand
#-------------------------------------------------------------------------------
class BuildCommand(Command):

    def __init__(self):
        Command.__init__(self, "build", "Builds chgr")

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('-c',
                            '--configurations',
                            help      = 'Configurations to build',
                            metavar   = "CONFIGURATION",
                            nargs     = '*',
                            default   = settings.default_build_configurations,
                            choices   = settings.build_configurations)

        parser.add_argument('-p',
                            '--platforms',
                            help      = 'Platforms to build',
                            metavar   = "PLATFORM",
                            nargs     = '*',
                            default   = settings.default_build_platforms,
                            choices   = settings.build_platforms)

        parser.add_argument('-r',
                             '--rebuild',
                             help     = 'Rebuild specified targets/platforms',
                             default  = False,
                             action   = "store_true")
        return True

    #---------------------------------------------------------------------------
    # run
    def run(self, context):
        settings        = context.settings
        local_directory = settings.local_directory
        build_directory = os.path.join(settings.solutions_directory, PREMAKE_ACTION)

        if OS == WINDOWS:
            return msvc_build(context, build_directory)
        elif OS == LINUX:
            make_build(context, build_directory)
        else:
            assert(False)

#-------------------------------------------------------------------------------
# msvc_build
def make_build(context, build_directory):
    arguments       = context.arguments
    platforms       = arguments.platforms
    configurations  = arguments.configurations
    rebuild         = arguments.rebuild

    if rebuild and not call_process(build_directory, ["make", "clean"]):
        return False
    for platform_it in platforms:
        for configuration_it in configurations:
            config_argument = "config={0}_{1}".format(configuration_it.lower(), platform_it.lower())
            if not call_process(build_directory, ["make", config_argument], convert_relative_paths):
                return False

#-------------------------------------------------------------------------------
# msvc_build
def msvc_build(context, build_directory):
    target_name         = None
    arguments           = context.arguments
    settings            = context.settings
    platforms           = arguments.platforms
    configurations      = arguments.configurations
    rebuild             = arguments.rebuild
    vs_tools_package    = VisualStudioToolsPackage()
    logger_path         = vs_tools_package.msbuild_logger_path(context)

    if logger_path is None:
        return False

    if rebuild:
        target_name = "Rebuild"
    else:
        target_name = "Build"

    for platform_it in platforms:
        for configuration_it in configurations:
            if not call_msbuild(settings, build_directory, platform_it, configuration_it, target_name, logger_path):
                return False

#-------------------------------------------------------------------------------
# call_msvc
def call_msbuild(settings, build_directory, platform, configuration, target, logger_path):
    sln_files       = regex_list_files(build_directory, ".*\.sln")
    msbuild_path    = find_msbuild_path(settings)

    if msbuild_path is None:
        log_error("Unable to find MSBuild, can't build solution in {0}", build_directory)
        return False

    if platform == "x32":
        platform = "Win32"

    for sln_file in sln_files:
        if not build_sln(settings, sln_file, msbuild_path, platform, configuration, target, logger_path):
            log_error("Error building {0} in {1}|{2}", sln_file, configuration, platform)
            return False

    return True

#-------------------------------------------------------------------------------
# find_msbuild_path
def find_msbuild_path(settings):
    msbuild_path = None
    for framework_version in settings.microsoft_framework_versions:
        msbuild_path_key_name_format = "SOFTWARE\\Microsoft\\MSBuild\\ToolsVersions\\{0}"
        msbuild_path_key_name        = msbuild_path_key_name_format.format(framework_version)
        msbuild_path                 = get_key_value(_winreg.HKEY_LOCAL_MACHINE,
                                                        msbuild_path_key_name,
                                                        "MSBuildToolsPath")
        if msbuild_path is not None:
            msbuild_path = os.path.join(msbuild_path, "MSBuild.exe")
            if os.path.exists(msbuild_path):
                break
    return msbuild_path

#-------------------------------------------------------------------------------
# build_sln
def build_sln(settings, sln_file, msbuild_path, platform, configuration, target, logger_path):
    build_directory     = os.path.dirname(sln_file)
    sln_file            = os.path.basename(sln_file)
    templated_arguments = []
    for argument_template in settings.msbuild_arguments_template:
        templated_argument = argument_template.format(platform = platform,
                                                      configuration = configuration,
                                                      target        = target,
                                                      logger_path   = logger_path)
        templated_arguments.append(templated_argument)
    msbuild_arguments = [msbuild_path] + templated_arguments + [sln_file]
    return call_process(build_directory, msbuild_arguments, crqr_tag_output_filter)

