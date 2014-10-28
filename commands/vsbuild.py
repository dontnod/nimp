# -*- coding: utf-8 -*-

#-------------------------------------------------------------------------------
# Imports
#-------------------------------------------------------------------------------
from commands.command       import *

from config.system          import *

from utilities.files        import *
from utilities.hashing      import *
from utilities.paths        import *
from utilities.processes    import *

#-------------------------------------------------------------------------------
# VsBuildCommand
#-------------------------------------------------------------------------------
class VsBuildCommand(Command):

    def __init__(self):
        Command.__init__(self, 'vsbuild', 'Build using Visual Studio')

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
                            nargs   = '*')

        parser.add_argument('-V',
                            '--version',
                            metavar = '<msvc_version>',
                            help    = 'Visual Studio version',
                            default = None)

        parser.add_argument('-t',
                             '--targets',
                            help    = 'targets (build, clean, rebuild)',
                            nargs   = '+',
                            default = 'build')

        parser.add_argument('-c',
                            '--configuration',
                            help    = 'configurations to build',
                            metavar = '<configuration>',
                            nargs   = '+',
                            default = settings.default_vsbuild_configurations)

        parser.add_argument('-p',
                            '--platform',
                            help    = 'platforms to build',
                            metavar = '<platform>',
                            nargs   = '+',
                            default = settings.default_vsbuild_platforms)
        return True

    #---------------------------------------------------------------------------
    # run
    def run(self, context):
        settings = context.settings
        arguments = context.arguments

        # Import settings

        build_directory = '.'
        versions = settings.visual_studio_versions
        targets = [ 'build' ]

        # Import arguments

        solution = arguments.solution
        projects = arguments.projects
        platforms = arguments.platform
        configurations = arguments.configuration

        if arguments.version is not None:
            versions = [ arguments.version ]

        if arguments.targets is not None:
            targets = arguments.targets

        # Validate environment

        devenv_path = _find_devenv_path(versions)
        if devenv_path is None:
            log_error('Unable to find Visual Studio {0}', ', or '.join(versions))
            return False

        # Run task

        cmdline = [ devenv_path, solution ]
        for devenv_args in _enumerate_devenv_args(configurations, platforms, targets, projects):
            if not call_process(build_directory, cmdline + devenv_args, nimp_tag_output_filter):
                return False
        return True

#-------------------------------------------------------------------------------
# _enumerate_devenv_args
def _enumerate_devenv_args(configurations, platforms, targets, projects):
    for configuration in configurations:
        for platform in platforms:
            for target in targets:
                args = [ '/' + target, configuration + '|' + platform ]
                if projects:
                    for project in projects:
                        yield [ '/project', project ] + args
                else:
                    yield args

#-------------------------------------------------------------------------------
# _find_devenv_path
def _find_devenv_path(versions):
    devenv_path = None
    for vs_version in versions:
        vstools_path = os.getenv('VS' + vs_version + '0COMNTOOLS')
        if vstools_path is not None:
            devenv_path = os.path.join(vstools_path, '../../Common7/IDE/devenv.com')
            if os.path.exists(devenv_path):
                log_verbose('Found Visual Studio at {0}', devenv_path)
                break
    return devenv_path

