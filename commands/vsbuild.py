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

#-------------------------------------------------------------------------------
# VsBuildCommand
#-------------------------------------------------------------------------------
class VsBuildCommand(Command):

    def __init__(self):
        Command.__init__(self, "vsbuild", "Build using Visual Studio")

    #---------------------------------------------------------------------------
    # configure_arguments
    def configure_arguments(self, context, parser):
        settings = context.settings

        parser.add_argument('solution',
                            metavar = '<solution>',
                            type    = str)

        parser.add_argument('projects',
                            metavar = '<project>',
                            type    = str,
                            nargs   = '+')

        parser.add_argument('-V',
                            '--version',
                            metavar = '<msvc_version>',
                            help    = 'Visual Studio version',
                            default = None)

        parser.add_argument('-r',
                             '--rebuild',
                            help    = 'Rebuild specified targets/platforms',
                            default = False,
                            action  = 'store_true')

        parser.add_argument('-c',
                            '--configuration',
                            help    = 'Configurations to build',
                            metavar = '<configuration>',
                            nargs   = '+',
                            default = settings.default_vsbuild_configurations)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'Platforms to build',
                            metavar = '<platform>',
                            nargs   = '+',
                            default = settings.default_vsbuild_platforms)
        return True

    #---------------------------------------------------------------------------
    # run
    def run(self, context):
        if OS != WINDOWS:
            return False

        settings        = context.settings
        arguments       = context.arguments

        solution        = arguments.solution
        projects        = arguments.projects
        versions        = settings.visual_studio_versions
        platforms       = arguments.platform
        configurations  = arguments.configuration
        target          = "Build"

        local_directory = settings.local_directory # FIXME: unused
        build_directory = settings.solutions_directory

        if arguments.version is not None:
            versions = [ arguments.version ]

        if arguments.rebuild is not None:
            target = "Rebuild"

        devenv_path = _find_devenv_path(settings, versions)
        if devenv_path is None:
            log_error("Unable to find Visual Studio {0}", versions)
            return False

        for (platform, configuration, project) in [(a, b, c) for a in platforms for b in configurations for c in projects]:
            if not _build_project(settings, devenv_path, build_directory, solution, target, project, platform, configuration):
                return False

#-------------------------------------------------------------------------------
# _build_project
def _build_project(settings, devenv_path, build_directory, solution, target, project, platform, configuration):
    cmdline = [ devenv_path,
                solution,
                "/project", project,
                "/" + target,
                configuration ]
    return call_process(build_directory, cmdline, nimp_tag_output_filter)

#-------------------------------------------------------------------------------
# _find_devenv_path
def _find_devenv_path(settings, versions):
    devenv_path = None
    for vs_version in versions:
        vstools_path = os.getenv("VS" + vs_version + "0COMNTOOLS")
        if vstools_path is not None:
            devenv_path = os.path.join(vstools_path, "../../Common7/IDE/devenv.com")
            if os.path.exists(devenv_path):
                log_verbose("Found Visual Studio at {0}", devenv_path)
                break
    return devenv_path

