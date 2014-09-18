# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
from commands.command       import *

from configuration.system   import *

from utilities.files        import *
from utilities.hashing      import *
from utilities.paths        import *
from utilities.processes    import *

if OS == WINDOWS:
    import _winreg
    from utilities.windows_utilities import *

#-------------------------------------------------------------------------------
# MsBuildCommand
#-------------------------------------------------------------------------------
class MsBuildCommand(Command):

    def __init__(self):
        Command.__init__(self, "msbuild", "Build using msbuild")

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('-P',
                            '--projects',
                            help    = 'Projects to build',
                            metavar = "PROJECT",
                            nargs   = '*',
                            default = None)

        parser.add_argument('-c',
                            '--configurations',
                            help    = 'Configurations to build',
                            metavar = "CONFIGURATION",
                            nargs   = '*',
                            default = [ 'Release' ])

        parser.add_argument('-p',
                            '--platforms',
                            help    = 'Platforms to build',
                            metavar = "PLATFORM",
                            nargs   = '*',
                            default = [ 'Win32' ])

        parser.add_argument('-r',
                             '--rebuild',
                            help    = 'Rebuild specified targets/platforms',
                            default = False,
                            action  = "store_true")
        return True

    #---------------------------------------------------------------------------
    # run
    def run(self, context):
        if OS != WINDOWS:
            return False

        settings        = context.settings
        arguments       = context.arguments

        target_name     = None
        projects        = arguments.projects
        platforms       = arguments.platforms
        configurations  = arguments.configurations
        rebuild         = arguments.rebuild
        logger_path     = "." # FIXME: no logger path available
        msbuild_path    = find_msbuild_path(settings)

        local_directory = settings.local_directory # FIXME: unused
        build_directory = settings.solutions_directory

        if rebuild:
            target_name = "Rebuild"
        else:
            target_name = "Build"

        if projects is None:
            targets = [target_name]
        else:
            targets = projects
            #targets = [p + ":" + target_name for p in projects]

        for platform_it in platforms:
            for configuration_it in configurations:
                 for target_it in targets:
                    if not call_msbuild(settings, msbuild_path, build_directory, platform_it, configuration_it, target_it, logger_path):
                        return False

#-------------------------------------------------------------------------------
# call_msvc
def call_msbuild(settings, msbuild_path, build_directory, platform, configuration, target, logger_path):
    sln_files = regex_list_files(build_directory, ".*2012.*[.]sln$") # FIXME (temp)

    if msbuild_path is None:
        log_error("Unable to find MSBuild, can't build solution in {0}",
                  build_directory)
        return False

    for sln_file in sln_files:
        if not build_sln(settings, sln_file, msbuild_path, platform, configuration, target, logger_path):
            log_error("Error executing {0} in {1} for {2}|{3}", target, sln_file, configuration, platform)
            return False

    return True

#-------------------------------------------------------------------------------
# find_msbuild_path
def find_msbuild_path(settings):
    msbuild_path = None
    for framework_version in settings.microsoft_framework_versions:
        msbuild_path_key_name_format = r"SOFTWARE\Microsoft\MSBuild\ToolsVersions\{0}"
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
    return call_process(build_directory, msbuild_arguments, nimp_tag_output_filter)

