# -*- coding: utf-8 -*-
# Copyright (c) 2014-2019 Dontnod Entertainment

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

''' Commands related to version packaging '''

import copy
import json
import glob
import logging
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree

import nimp.command
import nimp.environment
import nimp.system
import nimp.sys.process

from nimp.sys.platform import create_platform_desc


def _get_ini_value(file_path, key):
    ''' Retrieves a value from a ini file '''
    with open(file_path) as ini_file:
        ini_content = ini_file.read()
    match = re.search('^' + key + r'=(?P<value>.*?)$', ini_content, re.MULTILINE)
    if not match:
        raise KeyError('Key {key} was not found in {file_path}'.format(**locals()))
    return match.group('value')


def _try_remove(file_path, dry_run):

    def _remove():
        if os.path.isdir(file_path):
            if not dry_run:
                shutil.rmtree(file_path)
        elif os.path.isfile(file_path):
            if not dry_run:
                os.remove(file_path)

    # The operation can fail if Windows Explorer has a handle on the directory
    if os.path.exists(file_path):
        logging.info('Removing %s', file_path)
        nimp.system.try_execute(_remove, OSError)


def _try_create_directory(file_path, dry_run):

    def _create_directory():
        if not os.path.isdir(file_path):
            if not dry_run:
                os.makedirs(file_path)

    # The operation can fail if Windows Explorer has a handle on the directory
    if not os.path.isdir(file_path):
        nimp.system.try_execute(_create_directory, OSError)


def _copy_file(source, destination, dry_run):
    logging.info('Copying %s to %s', source, destination)
    if os.path.isdir(source):
        if not dry_run:
            os.makedirs(destination, exist_ok = True)
    elif os.path.isfile(source):
        if not dry_run:
            os.makedirs(os.path.dirname(destination), exist_ok = True)
            shutil.copyfile(source, destination)
    else:
        raise FileNotFoundError(source)


class UnrealPackageConfiguration():
    ''' Configuration to generate a game package from a Unreal project '''

    def __init__(self, env):
        self.env = env

        self.engine_directory = None
        self.project_directory = None
        self.configuration_directory = None
        self.resource_directory = None
        self.cook_directory = None
        self.patch_base_directory = None
        self.stage_directory = None
        self.package_directory = None

        self.project = None
        self.binary_configuration = None
        self.worker_platform = None
        self.cook_platform = None
        self.target_platform = None
        self.package_type = None
        self.shader_debug_info = False
        self.iterative_cook = False
        self.cook_extra_options = []
        self.pak_collection = []
        self.pak_compression = False
        self.pak_compression_exclusions = []
        self.layout_file_path = None
        self.ignored_errors = []
        self.ignored_warnings = []
        self.is_final_submission = False

        self.msixvc = False
        self.ps4_title_collection = []
        self.xbox_product_id = None
        self.xbox_content_id = None


class Package(nimp.command.Command):
    ''' Packages an unreal project for release '''

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'configuration', 'platform', 'free_parameters')

        all_steps = [ 'cook', 'stage', 'package', 'verify' ]
        default_steps = [ 'cook', 'stage', 'package' ]

        parser.add_argument('-n', '--dry-run', action = 'store_true', help = 'perform a test run, without writing changes')
        parser.add_argument('--steps', nargs = '+', choices = all_steps, default = default_steps, metavar = '<step>',
                            help = 'select the steps to execute\n(%s)' % ', '.join(all_steps))
        parser.add_argument('--variant', metavar = '<variant>', help = 'set the configuration variant to use')
        parser.add_argument('--iterate', action = 'store_true', help = 'enable iterative cooking')
        parser.add_argument('--shader-debug-info', action = 'store_true', help = 'enable shader debug information generation')
        parser.add_argument('--compress', action = 'store_true', help = 'enable pak file compression')
        parser.add_argument('--final', action = 'store_true', help = 'enable package options for final submission')
        parser.add_argument('--trackloadpackage', action = 'store_true', help = 'track LoadPackage calls when cooking')
        parser.add_argument('--cook-extra-options', nargs = '*', default = [], metavar = '<cook_option>',
                            help = 'pass additional options to the cook command')
        parser.add_argument('--msixvc', action = 'store_true', help = 'create a MSIXVC package')
        parser.add_argument('--ps4-regions', metavar = '<region>', nargs = '+', help = 'set the PS4 regions to package for')

        #region Legacy
        parser.add_argument('--layout', metavar = '<file_path>', help = '(deprecated) set the layout file to use for the package (for consoles)')
        parser.add_argument('--patch', action = 'store_true', help = '(deprecated) create a patch based on previously staged data')
        parser.add_argument('--ps4-title', nargs = '+', metavar = '<directory>',
                            help = '(deprecated) set the directory for the target title files (PS4 only, default to Unreal TitleID)')
        #endregion Legacy

        return True


    def is_available(self, env):
        return nimp.unreal.is_unreal4_available(env)


    def run(self, env):

        platform_desc = create_platform_desc(env.platform)
        if not platform_desc.is_valid:
            raise ValueError(f'Invalid platform {env.platform}')

        env.ue4_dir = env.ue4_dir.replace('\\', '/')
        env.cook_platform = nimp.unreal.get_cook_platform(env.ue4_platform)

        # Warning: do not move this outside env, because some .nimp.confs need it
        env.layout_file_extension = platform_desc.layout_file_extension
        if env.msixvc:
            env.layout_file_extension = 'xml'

        package_configuration = UnrealPackageConfiguration(env)

        package_configuration.engine_directory = nimp.system.standardize_path(env.format('{ue4_dir}/Engine'))
        package_configuration.project_directory = nimp.system.standardize_path(env.format('{uproject_dir}'))
        package_configuration.configuration_directory = nimp.system.standardize_path(env.format('{uproject_dir}/Config'))
        package_configuration.resource_directory = nimp.system.standardize_path(env.format('{uproject_dir}/Build/{ue4_platform}/Resources'))
        package_configuration.cook_directory = nimp.system.standardize_path(env.format('{uproject_dir}/Saved/Cooked/{cook_platform}'))
        package_configuration.patch_base_directory = nimp.system.standardize_path(env.format('{uproject_dir}/Saved/StagedBuilds/{cook_platform}-PatchBase'))
        package_configuration.stage_directory = nimp.system.standardize_path(env.format('{uproject_dir}/Saved/StagedBuilds/{cook_platform}'))
        package_configuration.package_directory = nimp.system.standardize_path(env.format(platform_desc.ue4_package_directory))

        if env.variant:
            variant_configuration_directory = package_configuration.configuration_directory + '/Variants/Active'
            if os.path.exists(variant_configuration_directory):
                package_configuration.configuration_directory = variant_configuration_directory
            variant_resource_directory = package_configuration.resource_directory + '/Variants/' + env.variant
            if os.path.exists(variant_resource_directory):
                package_configuration.resource_directory = variant_resource_directory

        package_configuration.project = env.game
        package_configuration.binary_configuration = env.ue4_config
        package_configuration.worker_platform = env.ue4_host_platform
        package_configuration.cook_platform = env.cook_platform
        package_configuration.target_platform = env.ue4_platform
        package_configuration.shader_debug_info = env.shader_debug_info
        package_configuration.iterative_cook = env.iterate
        package_configuration.cook_extra_options = env.cook_extra_options
        package_configuration.package_type = 'application'
        package_configuration.pak_collection = [ None ]
        package_configuration.pak_compression = env.compress
        package_configuration.is_microsoft = env.is_microsoft_platform
        package_configuration.is_sony = env.is_sony_platform
        package_configuration.is_final_submission = env.final
        package_configuration.msixvc = env.msixvc or env.platform == 'xboxone'

        package_configuration.package_tool_path = platform_desc.package_tool_path
        package_configuration.layout_file_extension = env.layout_file_extension

        # Temporary hack : PIO now uses "BuildEnvironment = TargetBuildEnvironment.Unique;"
        # https://jira.dont-nod.com/browse/XPJ-4747
        # https://gitea.dont-nod.com/devs/monorepo/commit/ceacad5c42cd0be34946236d36201e646b393d60
        #TODO: use .nimp.conf uniqueBuildEnvironment
        package_configuration.editor_path = package_configuration.engine_directory + '/Binaries/' + package_configuration.worker_platform
        package_configuration.editor_path += '/UE4Editor' + ('.exe' if package_configuration.worker_platform == 'Win64' else '')
        if not os.path.exists(package_configuration.editor_path):
            package_configuration.editor_path = package_configuration.project_directory + '/Binaries/' + package_configuration.worker_platform + '/'
            package_configuration.editor_path += package_configuration.project + 'Editor' + ('.exe' if package_configuration.worker_platform == 'Win64' else '')
        package_configuration.editor_cmd_exe = 'UE4Editor-Cmd.exe'
        if not os.path.exists(package_configuration.engine_directory + '/Binaries/Win64/' +  package_configuration.editor_cmd_exe):
            package_configuration.editor_cmd_exe = package_configuration.project + 'Editor-Cmd.exe'

        ps4_title_directory_collection = []

        if hasattr(env, 'package_variants'):
            if not env.variant:
                raise ValueError('Variant parameter is required')

            if 'type' in env.package_variants[env.variant]:
                package_configuration.package_type = env.package_variants[env.variant]['type']
            if 'content_paks' in env.package_variants[env.variant]:
                package_configuration.pak_collection = env.package_variants[env.variant]['content_paks']
            if 'content_compression_exclusions' in env.package_variants[env.variant]:
                package_configuration.pak_compression_exclusions = env.package_variants[env.variant]['content_compression_exclusions']
            if 'layout' in env.package_variants[env.variant]:
                package_configuration.layout_file_path = env.package_variants[env.variant]['layout']
            if 'ps4_titles' in env.package_variants[env.variant] and env.ps4_regions:
                ps4_title_directory_collection = [ env.package_variants[env.variant]['ps4_titles'][region] for region in env.ps4_regions ]
            if 'ignored_errors' in env.package_variants[env.variant]:
                package_configuration.ignored_errors = env.package_variants[env.variant]['ignored_errors']
            if 'ignored_warnings' in env.package_variants[env.variant]:
                package_configuration.ignored_warnings = env.package_variants[env.variant]['ignored_warnings']

        #region Legacy
        else:
            if env.patch:
                package_configuration.package_type = 'application_patch'
            if hasattr(env, 'content_paks'):
                package_configuration.pak_collection = env.content_paks
            if hasattr(env, 'content_compression_exclusions'):
                package_configuration.pak_compression_exclusions = env.content_compression_exclusions
            if env.variant and hasattr(env, 'content_paks_by_variant'):
                package_configuration.pak_collection = env.content_paks_by_variant[env.variant]
            if env.variant and env.platform in [ 'ps4', 'xboxone' ]:
                layout_file_name = ('PatchLayout' if env.patch else 'PackageLayout') + '.{variant}.{layout_file_extension}'
                package_configuration.layout_file_path = '{uproject_dir}/Build/{ue4_platform}/' + layout_file_name

        if env.layout:
            package_configuration.layout_file_path = env.layout
        if env.ps4_title:
            ps4_title_directory_collection = env.ps4_title
        #endregion Legacy

        if env.trackloadpackage:
            package_configuration.cook_extra_options.append('-TrackLoadPackage')

        if package_configuration.layout_file_path:
            package_configuration.layout_file_path = env.format(package_configuration.layout_file_path)
        ps4_title_directory_collection = [ env.format(title) for title in ps4_title_directory_collection ]

        Package._load_configuration(package_configuration, ps4_title_directory_collection)

        logging.info('')

        if 'cook' in env.steps:
            logging.info('=== Cook ===')
            Package.cook(env, package_configuration)
            logging.info('')
        if 'stage' in env.steps:
            logging.info('=== Stage ===')
            Package.stage(env, package_configuration)
            logging.info('')
        if 'package' in env.steps:
            logging.info('=== Package ===')
            Package.package_for_platform(env, package_configuration)
            logging.info('')
        if 'verify' in env.steps:
            logging.info('=== Verify ===')
            Package.verify(env, package_configuration)
            logging.info('')

        return True


    @staticmethod
    def _load_configuration(package_configuration, ps4_title_directory_collection):
        ''' Update configuration with information found in the project files '''

        if package_configuration.target_platform == 'PS4': # if package_configuration.is_sony:
            platform = package_configuration.target_platform
            if not ps4_title_directory_collection:
                ini_file_path = f'{package_configuration.configuration_directory}/{platform}/{platform}Engine.ini'
                ps4_title_directory_collection = [ _get_ini_value(ini_file_path, 'TitleID') ]

            ps4_title_collection = []
            for title_directory in ps4_title_directory_collection:
                title_json_path = f'{package_configuration.project_directory}/Build/{platform}/titledata/{title_directory}/title.json'
                with open(title_json_path) as title_json_file:
                    title_data = json.load(title_json_file)
                title_data['region'] = title_data['region'].upper()
                title_data['title_directory'] = title_directory
                ps4_title_collection.append(title_data)

            package_configuration.ps4_title_collection = ps4_title_collection

        if package_configuration.target_platform == 'XboxOne':
            ini_file_path = package_configuration.configuration_directory + '/XboxOne/XboxOneEngine.ini'
            package_configuration.xbox_product_id = _get_ini_value(ini_file_path, 'ProductId')
            package_configuration.xbox_content_id = _get_ini_value(ini_file_path, 'ContentId')


    @staticmethod
    def cook(env, package_configuration):
        ''' Build the project content for the target platform '''

        if package_configuration.package_type == 'entitlement':
            return

        logging.info('Cooking content for %s', package_configuration.target_platform)
        logging.info('')

        if not package_configuration.iterative_cook:
            _try_remove(package_configuration.cook_directory, env.dry_run)
            _try_create_directory(package_configuration.cook_directory, env.dry_run)

        nimp.environment.execute_hook('precook', env)

        cook_command = [
            package_configuration.editor_path, package_configuration.project,
            '-Run=Cook', '-TargetPlatform=' + package_configuration.cook_platform,
            '-BuildMachine', '-Unattended', '-StdOut', '-UTF8Output',
        ]
        if package_configuration.iterative_cook:
            cook_command += [ '-Iterate', '-IterateHash' ]
        cook_command += package_configuration.cook_extra_options

        if package_configuration.shader_debug_info:
            sdb_path = package_configuration.project_directory + '/Saved/ShaderDebugInfo/' + package_configuration.target_platform
            engine_configuration_file_path = package_configuration.configuration_directory + '/DefaultEngine.ini'

            if not env.dry_run:
                os.makedirs(sdb_path, exist_ok = True)
                shutil.move(engine_configuration_file_path, engine_configuration_file_path + '.nimp.bak')
                shutil.copyfile(engine_configuration_file_path + '.nimp.bak', engine_configuration_file_path)

        try:
            if package_configuration.shader_debug_info and not env.dry_run:
                with open(engine_configuration_file_path, 'a') as configuration_file:
                    configuration_file.write('\n')
                    configuration_file.write('[ConsoleVariables]\n')
                    configuration_file.write('r.DumpShaderDebugInfo=1\n')
                    configuration_file.write('r.DumpShaderDebugShortNames=1\n')
                    configuration_file.write('r.PS4DumpShaderSDB=1\n')
                    configuration_file.write('\n')
                    configuration_file.write('[DevOptions.Shaders]\n')
                    configuration_file.write('ShaderPDBRoot=' + os.path.abspath(sdb_path) + '\n')
                    configuration_file.write('\n')

            # Heartbeart for background shader compilation and existing cook verification
            cook_success = nimp.sys.process.call(cook_command, heartbeat = 60, dry_run = env.dry_run)
            if cook_success != 0:
                raise RuntimeError('Cook failed')

        finally:
            if package_configuration.shader_debug_info and not env.dry_run:
                os.remove(engine_configuration_file_path)
                shutil.move(engine_configuration_file_path + '.nimp.bak', engine_configuration_file_path)

        nimp.environment.execute_hook('postcook', env)


    @staticmethod
    def stage(env, package_configuration):
        ''' Gather the files required to generate a package '''

        logging.info('Staging package files for %s (Destination: %s)', package_configuration.target_platform, package_configuration.stage_directory)
        logging.info('')

        _try_remove(package_configuration.stage_directory, env.dry_run)
        _try_create_directory(package_configuration.stage_directory, env.dry_run)

        # AutomationTool is used here for the staging parts which are not done by nimp itself yet
        if package_configuration.package_type in [ 'application', 'application_patch' ]:
            stage_command = [
                package_configuration.engine_directory + '/Binaries/DotNET/AutomationTool.exe',
                'BuildCookRun', '-UE4exe=' + package_configuration.editor_cmd_exe, '-UTF8Output',
                '-Project=' + package_configuration.project,
                '-TargetPlatform=' + package_configuration.target_platform,
                '-ClientConfig=' + package_configuration.binary_configuration,
                '-SkipCook', '-Stage', '-Pak', '-Prereqs', '-CrashReporter', '-NoDebugInfo',
            ]

            if env.is_dne_legacy_ue4:
                stage_command += [ '-SkipPak' ]

            stage_success = nimp.sys.process.call(stage_command, dry_run = env.dry_run)
            if stage_success != 0:
                raise RuntimeError('Stage failed')

        Package._stage_title_files(package_configuration, env.dry_run)
        Package._stage_layout(package_configuration, env.dry_run)
        Package._stage_binaries(package_configuration, env.dry_run)
        Package._stage_content(env, package_configuration)

        if package_configuration.msixvc:
            if not env.dry_run:
                # Dummy files for empty chunks
                with open(package_configuration.stage_directory + '/LaunchChunk.bin', 'w') as empty_file:
                    empty_file.write('\0')
                with open(package_configuration.stage_directory + '/AlignmentChunk.bin', 'w') as empty_file:
                    empty_file.write('\0')


    @staticmethod
    def create_pak_file(env, package_configuration, pak_name, patch_base, destination):
        ''' Create a content archive with the Unreal pak format '''

        engine_binaries_directory = package_configuration.engine_directory + '/Binaries/' + package_configuration.worker_platform
        pak_tool_path = engine_binaries_directory + '/UnrealPak' + ('.exe' if package_configuration.worker_platform == 'Win64' else '')

        pak_file_name = package_configuration.project + '-' + package_configuration.cook_platform + (('-' + pak_name) if pak_name else '')

        # The pak file is created as a patch only if a base pak file exists.
        # The base package may include only a subset of pak files, additional pak files from the patch package will not use patch logic.
        # The patch base directory can be stripped of some pak files in order to bypass patch logic and overwrite the base pak file instead.
        is_patch = (package_configuration.package_type in [ 'application_patch', 'dlc_patch' ]) and os.path.isfile(patch_base + '/' + pak_file_name + '.pak')

        pak_file_path = destination + '/' + pak_file_name + ('_P' if is_patch else '') + '.pak'
        manifest_file_path = destination + '/' + pak_file_name + '.pak.txt'
        order_file_path = package_configuration.project_directory + '/Build/' + package_configuration.cook_platform + '/FileOpenOrder/GameOpenOrder.log'

        if package_configuration.target_platform == 'PS4':
            patch_base = patch_base.lower()
            destination = destination.lower()
            manifest_file_path = manifest_file_path.lower()
            pak_file_path = pak_file_path.lower()

        if not env.dry_run:
            os.makedirs(destination, exist_ok = True)

        logging.info('Listing files for pak %s', pak_file_name)
        file_mapper = nimp.system.FileMapper(None, vars(env))
        file_mapper.override(pak_name = pak_name).load_set('content_pak')
        all_files = file_mapper.to_list(env.root_dir, '.')

        if not all_files:
            logging.warning('No files for %s', pak_file_name)
            return

        logging.info('Creating manifest for pak %s', pak_file_name)
        if not env.dry_run:
            with open(manifest_file_path, 'w') as manifest_file:
                for source_file, destination_file in all_files:
                    allow_compression = os.path.basename(source_file) not in package_configuration.pak_compression_exclusions
                    options = '-Compress' if package_configuration.pak_compression and allow_compression else ''
                    manifest_file.write('"%s" "%s" %s\n' % (os.path.abspath(source_file).replace('\\', '/'), '../../../' + destination_file, options))

        logging.info('Creating pak %s', pak_file_name)
        pak_command = [
            pak_tool_path, os.path.abspath(pak_file_path),
            '-Create=' + os.path.abspath(manifest_file_path),
            '-Order=' + os.path.abspath(order_file_path),
        ]

        # From AutomationTool GetPlatformPakCommandLine
        if package_configuration.target_platform == 'Win64':
            pak_command += [ '-PatchPaddingAlign=2048' ]
        elif package_configuration.target_platform == 'PS4':
            pak_command += [ '-BlockSize=256MB', '-PatchPaddingAlign=65536' ]
        elif package_configuration.target_platform == 'XboxOne':
            pak_command += [ '-BlockSize=4KB', '-BitWindow=12' ]

        if is_patch:
            pak_command += [ '-GeneratePatch=' + os.path.abspath(patch_base + '/' + pak_file_name + '.pak') ]

        pak_success = nimp.sys.process.call(pak_command, dry_run = env.dry_run)
        if pak_success != 0:
            raise RuntimeError('Pak creation failed')


    @staticmethod
    def _stage_title_files(package_configuration, dry_run):

        if package_configuration.target_platform == 'PS4':

            # AutomationTool already stages these files
            if package_configuration.package_type in [ 'application', 'application_patch']:
                return

            mapping_collection = [
                (package_configuration.project_directory + '/Build/PS4/sce_sys/{title_directory}', 'sce_sys/{title_directory}'),
                (package_configuration.project_directory + '/Build/PS4/titledata/{title_directory}/title.json', '{title_directory}/title.json'),
            ]

            for title in package_configuration.ps4_title_collection:
                for source_path, destination_path in mapping_collection:
                    source_path = source_path.format(title_directory = title['title_directory'])
                    destination_path = destination_path.format(title_directory = title['title_directory']).lower()
                    Package._stage_file(package_configuration.stage_directory, source_path, destination_path, dry_run)

        elif package_configuration.target_platform == 'XboxOne':

            # AutomationTool already stages these files
            if package_configuration.package_type in [ 'application', 'application_patch'] and not dry_run:
                os.remove(package_configuration.stage_directory + '/AppxManifest.xml')
                os.remove(package_configuration.stage_directory + '/appdata.bin')
                os.remove(package_configuration.stage_directory + '/resources.pri')
                shutil.rmtree(package_configuration.stage_directory + '/Resources')

            manifest_source = package_configuration.configuration_directory + '/XboxOne/AppxManifest.xml'
            transform_parameters = {}
            for binary_configuration in package_configuration.binary_configuration.split('+'):
                manifest_destination = 'AppxManifest-%s.xml' % binary_configuration
                transform_parameters['executable_name'] = Package._get_executable_name(package_configuration, binary_configuration)
                transform_parameters['configuration'] = binary_configuration
                Package._stage_and_transform_file(package_configuration.stage_directory, manifest_source, manifest_destination, transform_parameters, dry_run)

            resource_file_collection = glob.glob(package_configuration.resource_directory + '/**/*.png', recursive = True)
            resource_file_collection += glob.glob(package_configuration.resource_directory + '/**/*.resw', recursive = True)
            resource_file_collection = [ nimp.system.standardize_path(path) for path in resource_file_collection ]
            for resource_source in resource_file_collection:
                resource_destination = 'Resources/' + os.path.relpath(resource_source, package_configuration.resource_directory)
                Package._stage_file(package_configuration.stage_directory, resource_source, resource_destination, dry_run)

            xdk_root = os.environ.get('DurangoXDK', None) or '/'
            makepri_command = [
                os.path.join(xdk_root, 'bin', 'MakePri.exe'), 'new',
                '/ProjectRoot', package_configuration.stage_directory,
                '/ConfigXml', package_configuration.project_directory + '/Build/XboxOne/PriConfig.xml',
                '/Manifest', package_configuration.configuration_directory + '/XboxOne/AppxManifest.xml',
                '/OutputFile', package_configuration.stage_directory + '/resources.pri',
                '/IndexLog', package_configuration.stage_directory + '/resources.log.xml',
            ]

            logging.info('+ %s', ' '.join(makepri_command))
            if not dry_run:
                subprocess.check_call(makepri_command)

        elif package_configuration.target_platform == 'Win64' and package_configuration.msixvc:

            if os.path.exists(package_configuration.configuration_directory + '/Windows/AppxManifest.xml'):
                manifest_source = package_configuration.configuration_directory + '/Windows/AppxManifest.xml'
                manifest_destination_format = 'AppxManifest-{configuration}.xml'
            elif os.path.exists(package_configuration.configuration_directory + '/Windows/MicrosoftGame.config'):
                manifest_source = package_configuration.configuration_directory + '/Windows/MicrosoftGame.config'
                manifest_destination_format = 'MicrosoftGame-{configuration}.config'
            else:
                raise FileNotFoundError("MSIXVC packaging requires 'AppxManifest.xml' or 'MicrosoftGame.config'")

            transform_parameters = {}
            for binary_configuration in package_configuration.binary_configuration.split('+'):
                manifest_destination = manifest_destination_format.format(configuration = binary_configuration)
                transform_parameters['executable_name'] = Package._get_executable_name(package_configuration, binary_configuration)
                transform_parameters['configuration'] = binary_configuration
                Package._stage_and_transform_file(package_configuration.stage_directory, manifest_source, manifest_destination, transform_parameters, dry_run)

            resource_file_collection = glob.glob(package_configuration.resource_directory + '/**/*.png', recursive = True)
            resource_file_collection += glob.glob(package_configuration.resource_directory + '/**/*.resw', recursive = True)
            resource_file_collection = [ nimp.system.standardize_path(path) for path in resource_file_collection ]
            for resource_source in resource_file_collection:
                resource_destination = 'Resources/' + os.path.relpath(resource_source, package_configuration.resource_directory)
                Package._stage_file(package_configuration.stage_directory, resource_source, resource_destination, dry_run)

            sdk_root = os.environ.get('GamingSDK', None) or '/'
            makepri_command = [
                os.path.join(sdk_root, 'bin', 'MakePri.exe'), 'new',
                '/ProjectRoot', package_configuration.stage_directory,
                '/ConfigXml', package_configuration.project_directory + '/Build/Win64/PriConfig.xml',
                '/IndexName', xml.etree.ElementTree.parse(manifest_source).getroot().find('Identity').get('Name'),
                '/OutputFile', package_configuration.stage_directory + '/resources.pri',
                '/IndexLog', package_configuration.stage_directory + '/resources.log.xml',
            ]

            logging.info('+ %s', ' '.join(makepri_command))
            if not dry_run:
                subprocess.check_call(makepri_command)


    @staticmethod
    def _stage_binaries(package_configuration, dry_run):
        if package_configuration.package_type not in [ 'application', 'application_patch' ]:
            return

        source = '{project_directory}/Binaries/{target_platform}'.format(**vars(package_configuration))
        destination = '{project}/Binaries/{target_platform}'.format(**vars(package_configuration))

        # AutomationTool already stages executables and symbol metadata
        if package_configuration.target_platform in [ 'Win64', 'XboxOne' ]:
            for binary_configuration in package_configuration.binary_configuration.split('+'):
                pdb_file_name = Package._get_executable_name(package_configuration, binary_configuration) + '.pdb'
                Package._stage_file(package_configuration.stage_directory, source + '/' + pdb_file_name, destination + '/' + pdb_file_name, dry_run)


    @staticmethod
    def _stage_layout(package_configuration, dry_run):
        source = package_configuration.layout_file_path
        format_parameters = { 'project': package_configuration.project, 'platform': package_configuration.target_platform }

        if package_configuration.target_platform == 'PS4': # if package_configuration.is_sony:
            for title_data in package_configuration.ps4_title_collection:
                transform_parameters = copy.deepcopy(title_data)
                transform_parameters['title_directory'] = transform_parameters['title_directory'].lower()
                for binary_configuration in package_configuration.binary_configuration.split('+'):
                    format_parameters['configuration'] = binary_configuration
                    format_parameters['region'] = title_data['region']
                    format_parameters['layout_file_extension'] = package_configuration.layout_file_extension
                    destination = '{project}-{region}-{configuration}.{layout_file_extension}'.format(**format_parameters).lower()
                    transform_parameters['executable_name'] = Package._get_executable_name(package_configuration, binary_configuration).lower()
                    transform_parameters['configuration'] = binary_configuration.lower()
                    Package._stage_and_transform_file(package_configuration.stage_directory, source, destination, transform_parameters, dry_run)

        elif package_configuration.msixvc:
            transform_parameters = {}
            for binary_configuration in package_configuration.binary_configuration.split('+'):
                format_parameters['configuration'] = binary_configuration
                destination = '{project}-{configuration}.xml'.format(**format_parameters)
                transform_parameters['executable_name'] = Package._get_executable_name(package_configuration, binary_configuration)
                transform_parameters['configuration'] = binary_configuration
                Package._stage_and_transform_file(package_configuration.stage_directory, source, destination, transform_parameters, dry_run)


    @staticmethod
    def _stage_content(env, package_configuration):
        if package_configuration.package_type == 'entitlement':
            return

        try:
            file_mapper = nimp.system.FileMapper(None, vars(env))
            file_mapper.load_set('content_other')
            all_files = file_mapper.to_list(env.root_dir, '.')
            for source_file, destination_file in all_files:
                if package_configuration.target_platform == 'PS4':
                    destination_file = destination_file.lower()
                Package._stage_file(package_configuration.stage_directory, source_file, destination_file, env.dry_run)
        except ImportError:
            pass

        pak_patch_base = '{patch_base_directory}/{project}/Content/Paks'.format(**vars(package_configuration))
        pak_destination_directory = '{stage_directory}/{project}/Content/Paks'.format(**vars(package_configuration))
        for pak_name in package_configuration.pak_collection:
            Package.create_pak_file(env, package_configuration, pak_name, pak_patch_base, pak_destination_directory)


    @staticmethod
    def _stage_file(stage_directory, source, destination, dry_run):
        logging.info('Staging %s as %s', source, destination)
        if os.path.isdir(source):
            if not dry_run:
                shutil.copytree(source, stage_directory + '/' + destination, copy_function = shutil.copyfile)
        elif os.path.isfile(source):
            if not dry_run:
                os.makedirs(os.path.dirname(stage_directory + '/' +destination), exist_ok = True)
                shutil.copyfile(source, stage_directory + '/' +destination)
        else:
            raise FileNotFoundError(source)


    @staticmethod
    def _stage_and_transform_file(stage_directory, source, destination, transform_parameters, dry_run):
        logging.info('Staging %s as %s', source, destination)

        with open(source, 'r') as source_file:
            file_content = source_file.read()
        file_content = file_content.format(**transform_parameters)
        if transform_parameters['configuration'].lower() == 'shipping':
            file_content = re.sub(r'<!-- #if Debug -->(.*?)<!-- #endif Debug -->', '', file_content, 0, re.DOTALL)

        if not dry_run:
            with open(stage_directory + '/' + destination, 'w') as destination_file:
                destination_file.write(file_content)


    @staticmethod
    def _get_executable_name(package_configuration, configuration):
        format_parameters = {
            'project': package_configuration.project,
            'platform': package_configuration.target_platform,
            'configuration': configuration,
        }

        suffix = '-{platform}-{configuration}' if configuration != 'Development' else ''
        return ('{project}' + suffix).format(**format_parameters)


    @staticmethod
    def package_for_platform(env, package_configuration):
        ''' Generate a package for a target platform '''

        logging.info('Packaging for %s (Source: %s, Destination: %s)', package_configuration.target_platform,
                     package_configuration.stage_directory, package_configuration.package_directory)
        logging.info('')

        if package_configuration.target_platform in [ 'Linux', 'Mac', 'Win32', 'Win64' ]:
            if package_configuration.target_platform == 'Win64' and package_configuration.msixvc:
                Package.package_for_windows_msixvc(package_configuration, env.dry_run)
            else:
                Package.package_for_desktop(package_configuration, vars(env), env.dry_run)
        # legacy console packaging
        elif package_configuration.target_platform == 'PS4':
            Package.package_for_sony(package_configuration, env.dry_run)
        elif package_configuration.target_platform == 'XboxOne':
            Package.package_for_xboxone(package_configuration, env.dry_run)
        # console packaging using out of the box uat behavior
        elif package_configuration.is_sony or package_configuration.is_microsoft:
            Package.package_with_uat(package_configuration, env.dry_run)


    @staticmethod
    def package_for_desktop(package_configuration, file_mapper_arguments, dry_run):
        source = package_configuration.stage_directory
        destination = 'Default-Final' if package_configuration.is_final_submission else 'Default'
        destination = package_configuration.package_directory + '/' + destination
        _try_remove(destination, dry_run)
        _try_create_directory(destination, dry_run)

        logging.info('Listing package files')
        file_mapper = nimp.system.FileMapper(None, file_mapper_arguments)
        file_mapper.load_set('stage_to_package')
        all_files = file_mapper.to_list(source, destination)

        for source_file, destination_file in all_files:
            _copy_file(source_file, destination_file, dry_run)


    def package_with_uat(package_configuration, dry_run):
        # Packaging with out of the box UAT behavior
        destination = package_configuration.package_directory
        if not os.path.isdir(destination):
            raise IOError('Package failed: %s does not exist.' % destination )
        # Cautionnary cleaning
        for item in os.listdir(destination):
            if item.endswith('.pkg') or\
               item.endswith('.msixvc') or item.endswith('.msixvc.phd') or\
               item.endswith('.ekb') or item.endswith('.zip') or\
               item.endswith('.' + package_configuration.layout_file_extension):
                _try_remove(os.path.join(destination, item), dry_run)

        if package_configuration.package_type in [ 'application', 'application_patch' ]:
            package_command = [
                package_configuration.engine_directory + '/Binaries/DotNET/AutomationTool.exe',
                'BuildCookRun', '-UE4exe=' + package_configuration.editor_cmd_exe, '-UTF8Output',
                '-Project=' + package_configuration.project,
                '-TargetPlatform=' + package_configuration.target_platform,
                '-ClientConfig=' + package_configuration.binary_configuration,
                '-SkipCook', '-SkipStage', '-Package',
            ]

            package_success = nimp.sys.process.call(package_command, dry_run = dry_run)
            if package_success != 0:
                raise RuntimeError('Package failed')


    @staticmethod
    def package_for_sony(package_configuration, dry_run):
        source = package_configuration.stage_directory
        package_tool_path = package_configuration.package_tool_path

        for title_data in package_configuration.ps4_title_collection:
            for binary_configuration in package_configuration.binary_configuration.split('+'):
                destination = title_data['region'] + '-' + binary_configuration + ('-Final' if package_configuration.is_final_submission else '')
                destination = package_configuration.package_directory + '/' + destination
                layout_file = source + '/' + package_configuration.project + '-' + title_data['region'] + '-' + binary_configuration + '.' + package_configuration.layout_file_extension
                output_format = 'pkg'
                if package_configuration.is_final_submission:
                    if package_configuration.package_type == 'application' and title_data['storagetype'].startswith('bd'):
                        output_format += '+iso'
                    output_format += '+subitem'


                _try_remove(destination, dry_run)
                _try_remove(destination + '-Temporary', dry_run)
                _try_create_directory(destination, dry_run)
                _try_create_directory(destination + '-Temporary', dry_run)

                create_package_command = [
                    package_tool_path, 'img_create',
                    '--no_progress_bar',
                    '--tmp_path', destination + '-Temporary',
                    '--oformat', output_format,
                    layout_file, destination
                ]

                package_success = nimp.sys.process.call(create_package_command, dry_run = dry_run)
                if package_success != 0:
                    raise RuntimeError('Package generation failed')

                _try_remove(destination + '-Temporary', dry_run)


    @staticmethod
    def package_for_xboxone(package_configuration, dry_run):
        package_tool_path = package_configuration.package_tool_path
        source = package_configuration.stage_directory

        for binary_configuration in package_configuration.binary_configuration.split('+'):
            destination = binary_configuration + ('-Final' if package_configuration.is_final_submission else '')
            destination = package_configuration.package_directory + '/' + destination
            layout_file_path = source + '/' + package_configuration.project + '-' + binary_configuration + '.xml'

            Package.verify_msixvc_files(source, layout_file_path)

            package_command = [ package_tool_path, 'pack', '/v' ]
            package_command += [ '/f', layout_file_path, '/d', source, '/pd', destination ]
            package_command += [ '/productid', package_configuration.xbox_product_id ]
            package_command += [ '/contentid', package_configuration.xbox_content_id ]
            package_command += [ '/l' ] if package_configuration.is_final_submission else []

            if package_configuration.package_type in [ 'application', 'application_patch' ]:
                package_command += [ '/genappdata', '/gameos', source + '/era.xvd' ]

            _try_remove(destination, dry_run)
            _try_create_directory(destination, dry_run)

            if not dry_run:
                shutil.copyfile(source + '/AppxManifest-%s.xml' % binary_configuration, source + '/AppxManifest.xml')

            package_success = nimp.sys.process.call(package_command, dry_run = dry_run)

            if not dry_run:
                os.remove(source + '/AppxManifest.xml')
                if os.path.isfile(source + '/appdata.bin'):
                    os.remove(source + '/appdata.bin')

            if package_success != 0:
                raise RuntimeError('Package generation failed')


    @staticmethod
    def package_for_windows_msixvc(package_configuration, dry_run):
        sdk_root = os.environ.get('GamingSDK', None) or '/'
        package_tool_path = os.path.join(sdk_root, 'bin', 'MakePkg.exe')
        source = package_configuration.stage_directory

        for binary_configuration in package_configuration.binary_configuration.split('+'):
            destination = 'MSIXVC' + '-' + binary_configuration + ('-' + 'Final' if package_configuration.is_final_submission else '')
            destination = package_configuration.package_directory + '/' + destination
            layout_file_path = source + '/' + package_configuration.project + '-' + binary_configuration + '.xml'

            Package.verify_msixvc_files(source, layout_file_path)

            package_command = [ package_tool_path, 'pack', '/v', '/pc' ]
            package_command += [ '/f', layout_file_path, '/d', source, '/pd', destination ]
            package_command += [ '/l' ] if package_configuration.is_final_submission else []

            _try_remove(destination, dry_run)
            _try_create_directory(destination, dry_run)

            if not dry_run:
                if os.path.isfile(source + '/AppxManifest-%s.xml' % binary_configuration):
                    shutil.copyfile(source + '/AppxManifest-%s.xml' % binary_configuration, source + '/AppxManifest.xml')
                if os.path.isfile(source + '/MicrosoftGame-%s.config' % binary_configuration):
                    shutil.copyfile(source + '/MicrosoftGame-%s.config' % binary_configuration, source + '/MicrosoftGame.config')

            package_success = nimp.sys.process.call(package_command, dry_run = dry_run)

            if not dry_run:
                if os.path.isfile(source + '/AppxManifest.xml'):
                    os.remove(source + '/AppxManifest.xml')
                if os.path.isfile(source + '/appdata.bin'):
                    os.remove(source + '/appdata.bin')
                if os.path.isfile(source + '/MicrosoftGame.config'):
                    os.remove(source + '/MicrosoftGame.config')

            if package_success != 0:
                raise RuntimeError('Package generation failed')


    @staticmethod
    def verify_msixvc_files(stage_directory, layout_file_path):
        layout_xml = xml.etree.ElementTree.parse(layout_file_path).getroot()

        file_not_found = False
        for chunk in layout_xml.findall('Chunk'):
            for file_group in chunk.findall('FileGroup'):
                if file_group.get("Include").lower() in [ "microsoftgame.config", "appxmanifest.xml", "appdata.bin" ]:
                    continue
                file_pattern = stage_directory + "/" + file_group.get('SourcePath') + "/" + file_group.get("Include")
                if not glob.glob(file_pattern):
                    file_not_found = True
                    logging.error("Files not found: '%s'", file_pattern)
        if file_not_found:
            raise FileNotFoundError


    @staticmethod
    def verify(env, package_configuration):
        ''' Verify the generated packages '''

        logging.info('Verifying packages (Path: %s)', package_configuration.package_directory)
        logging.info('')

        if package_configuration.target_platform == 'Win64':
            Package.verify_for_windows(package_configuration)
        elif package_configuration.target_platform == 'PS4':
            Package.verify_for_ps4(package_configuration, env.dry_run)
        elif package_configuration.target_platform == 'XboxOne':
            Package.verify_for_xboxone(package_configuration)


    @staticmethod
    def verify_for_ps4(package_configuration, dry_run):
        package_tool_path = package_configuration.package_tool_path

        for title_data in package_configuration.ps4_title_collection:
            for binary_configuration in package_configuration.binary_configuration.split('+'):
                directory = title_data['region'] + '-' + binary_configuration + ('-Final' if package_configuration.is_final_submission else '')
                directory = package_configuration.package_directory + '/' + directory

                _try_remove(directory + '-Temporary', dry_run)
                _try_create_directory(directory + '-Temporary', dry_run)

                validate_package_command = [
                    package_tool_path, 'img_verify',
                    '--no_progress_bar',
                    '--tmp_path', directory + '-Temporary',
                    '--passcode', title_data['title_passcode'],
                ]
                validate_package_command += [ path.replace('\\', '/') for path in glob.glob(directory + '/*.pkg') ]

                validation_success = nimp.sys.process.call(validate_package_command, dry_run = dry_run)
                if validation_success != 0:
                    logging.warning('Package validation failed')

                _try_remove(directory + '-Temporary', dry_run)


    @staticmethod
    def verify_for_xboxone(package_configuration):
        for binary_configuration in package_configuration.binary_configuration.split('+'):
            package_directory = binary_configuration + ('-' + 'Final' if package_configuration.is_final_submission else '')
            package_directory = package_configuration.package_directory + '/' + package_directory
            Package.verify_msixvc(package_directory, package_configuration.ignored_errors, package_configuration.ignored_warnings)


    @staticmethod
    def verify_for_windows(package_configuration):
        if package_configuration.msixvc:
            for binary_configuration in package_configuration.binary_configuration.split('+'):
                package_directory = 'MSIXVC' + '-' + binary_configuration + ('-' + 'Final' if package_configuration.is_final_submission else '')
                package_directory = package_configuration.package_directory + '/' + package_directory
                Package.verify_msixvc(package_directory, package_configuration.ignored_errors, package_configuration.ignored_warnings)


    @staticmethod
    def verify_msixvc(package_directory, ignored_errors, ignored_warnings):
        validation_success = True
        for validator_path in [ path.replace('\\', '/') for path in glob.glob(package_directory + '/Validator_*.xml') ]:
            logging.info('Reading %s', validator_path)
            validator_xml = xml.etree.ElementTree.parse(validator_path).getroot()
            for test_result in validator_xml.find('testresults').findall('testresult'):
                for failure in test_result.findall('.//failure'):
                    if failure.text not in ignored_errors:
                        logging.error('%s: %s', test_result.find('component').text, failure.text)
                        validation_success = False
                for warning in test_result.findall('.//warning'):
                    if warning.text not in ignored_warnings:
                        logging.warning('%s: %s', test_result.find('component').text, warning.text)
                        validation_success = False

        if not validation_success:
            logging.warning('Package validation failed')
