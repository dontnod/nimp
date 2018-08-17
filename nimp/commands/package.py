# Copyright (c) 2014-2018 Dontnod Entertainment

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# 'Software'), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
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
import xml.etree.ElementTree

import nimp.commands
import nimp.environment
import nimp.system
import nimp.sys.process


def _get_ini_value(file_path, key):
    ''' Retrieves a value from a ini file '''
    with open(file_path) as ini_file:
        ini_content = ini_file.read()
    match = re.search('^' + key + r'=(?P<value>.*?)$', ini_content, re.MULTILINE)
    if not match:
        raise KeyError('Key {key} was not found in {file_path}'.format(**locals()))
    return match.group('value')


def _try_remove(file_path, simulate):

    def _remove():
        if os.path.isdir(file_path):
            if not simulate:
                shutil.rmtree(file_path)
        elif os.path.isfile(file_path):
            if not simulate:
                os.remove(file_path)

    # The operation can fail if Windows Explorer has a handle on the directory
    if os.path.exists(file_path):
        logging.info('Removing %s', file_path)
        nimp.system.try_execute(_remove, OSError)


def _try_create_directory(file_path, simulate):

    def _create_directory():
        if not os.path.isdir(file_path):
            if not simulate:
                os.makedirs(file_path)

    # The operation can fail if Windows Explorer has a handle on the directory
    if not os.path.isdir(file_path):
        nimp.system.try_execute(_create_directory, OSError)


def _copy_file(source, destination, simulate):
    logging.info('Copying %s to %s', source, destination)
    if os.path.isdir(source):
        if not simulate:
            os.makedirs(destination, exist_ok = True)
    elif os.path.isfile(source):
        if not simulate:
            os.makedirs(os.path.dirname(destination), exist_ok = True)
            shutil.copyfile(source, destination)
    else:
        raise FileNotFoundError(source)


class UnrealPackageConfiguration():
    ''' Configuration to generate a game package from a Unreal project '''

    def __init__(self):
        self.engine_directory = None
        self.project_directory = None
        self.configuration_directory = None
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
        self.iterative_cook = False
        self.cook_extra_options = []
        self.pak_collection = []
        self.pak_compression = False
        self.pak_compression_exclusions = []
        self.layout_file_path = None
        self.is_final_submission = False

        self.ps4_title_collection = []
        self.xbox_product_id = None
        self.xbox_content_id = None


class Package(nimp.command.Command):
    ''' Packages an unreal project for release '''

    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'configuration', 'platform', 'free_parameters')

        all_steps = [ 'cook', 'stage', 'package', 'verify' ]
        default_steps = [ 'cook', 'stage', 'package' ]

        parser.add_argument('--simulate', action = 'store_true', help = 'perform a test run, without writing changes')
        parser.add_argument('--steps', nargs = '+', choices = all_steps, default = default_steps, metavar = '<step>',
                            help = 'select the steps to execute\n(%s)' % ', '.join(all_steps))
        parser.add_argument('--variant', metavar = '<variant>', help = 'set the configuration variant to use')
        parser.add_argument('--iterate', action = 'store_true', help = 'enable iterative cooking')
        parser.add_argument('--compress', action = 'store_true', help = 'enable pak file compression')
        parser.add_argument('--final', action = 'store_true', help = 'enable package options for final submission')
        parser.add_argument('--trackloadpackage', action = 'store_true', help = 'track LoadPackage calls when cooking')
        parser.add_argument('--cook-extra-options', nargs = '*', default = [], metavar = '<cook_option>',
                            help = 'pass additional options to the cook command')
        parser.add_argument('--ps4-regions', metavar = '<region>', nargs = '+', help = 'Set the PS4 regions to package for')

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
        env.root_dir = env.root_dir.replace('\\', '/')
        env.worker_platform = nimp.unreal.get_host_platform()
        env.cook_platform = nimp.unreal.get_cook_platform(env.ue4_platform)
        if env.platform == 'ps4':
            env.layout_file_extension = 'gp4'
        elif env.platform == 'xboxone':
            env.layout_file_extension = 'xml'

        package_configuration = UnrealPackageConfiguration()

        package_configuration.engine_directory = env.format('{root_dir}/Engine')
        package_configuration.project_directory = env.format('{root_dir}/{game}')
        package_configuration.configuration_directory = env.format('{root_dir}/{game}/Config')
        package_configuration.cook_directory = env.format('{root_dir}/{game}/Saved/Cooked/{cook_platform}')
        package_configuration.patch_base_directory = env.format('{root_dir}/{game}/Saved/StagedBuilds/{cook_platform}-PatchBase')
        package_configuration.stage_directory = env.format('{root_dir}/{game}/Saved/StagedBuilds/{cook_platform}')
        package_configuration.package_directory = env.format('{root_dir}/{game}/Saved/Packages/{cook_platform}')

        variant_configuration_directory = package_configuration.configuration_directory + '/Variants/Active'
        if os.path.exists(variant_configuration_directory):
            package_configuration.configuration_directory = variant_configuration_directory

        package_configuration.project = env.game
        package_configuration.binary_configuration = env.ue4_config
        package_configuration.worker_platform = env.worker_platform
        package_configuration.cook_platform = env.cook_platform
        package_configuration.target_platform = env.ue4_platform
        package_configuration.iterative_cook = env.iterate
        package_configuration.cook_extra_options = env.cook_extra_options
        package_configuration.package_type = 'application'
        package_configuration.pak_collection = [ None ]
        package_configuration.pak_compression = env.compress
        package_configuration.is_final_submission = env.final

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
                package_configuration.layout_file_path = '{root_dir}/{game}/Build/{ue4_platform}/' + layout_file_name

        if env.layout:
            package_configuration.layout_file_path = env.layout
        if env.ps4_title:
            ps4_title_directory_collection = env.ps4_title
        #endregion Legacy

        if env.trackloadpackage:
            package_configuration.cook_extra_options.append('-TrackLoadPackage')

        if env.platform not in [ 'ps4', 'xboxone' ]:
            package_configuration.layout_file_path = None
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

        if package_configuration.target_platform == 'PS4':
            if not ps4_title_directory_collection:
                ini_file_path = package_configuration.configuration_directory + '/PS4/PS4Engine.ini'
                ps4_title_directory_collection = [ _get_ini_value(ini_file_path, 'TitleID') ]

            ps4_title_collection = []
            for title_directory in ps4_title_directory_collection:
                title_json_path = package_configuration.project_directory + '/Build/PS4/titledata/' + title_directory + '/title.json'
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
            _try_remove(package_configuration.cook_directory, env.simulate)
            _try_create_directory(package_configuration.cook_directory, env.simulate)

        nimp.environment.execute_hook('precook', env)

        engine_binaries_directory = package_configuration.engine_directory + '/Binaries/' + package_configuration.worker_platform
        editor_path = engine_binaries_directory + '/UE4Editor' + ('.exe' if package_configuration.worker_platform == 'Win64' else '')

        cook_command = [
            editor_path, package_configuration.project,
            '-Run=Cook', '-TargetPlatform=' + package_configuration.cook_platform,
            '-BuildMachine', '-Unattended', '-StdOut', '-UTF8Output',
        ]
        if package_configuration.iterative_cook:
            cook_command += [ '-Iterate', '-IterateHash' ]
        cook_command += package_configuration.cook_extra_options

        configuration_file_path = package_configuration.configuration_directory + '/DefaultEngine.ini'
        sdb_path = package_configuration.project_directory + '/Saved/ShaderDebugInfo/' + package_configuration.target_platform

        if not env.simulate:
            if not os.path.isdir(sdb_path):
                os.makedirs(sdb_path)
            shutil.move(configuration_file_path, configuration_file_path + '.bak')
            shutil.copyfile(configuration_file_path + '.bak', configuration_file_path)

        try:
            if not env.simulate:
                with open(configuration_file_path, 'a') as configuration_file:
                    configuration_file.write('\n')
                    configuration_file.write('[DevOptions.Shaders]\n')
                    configuration_file.write('ShaderPDBRoot=' + os.path.abspath(sdb_path) + '\n')
                    configuration_file.write('\n')

            # Heartbeart for background shader compilation and existing cook verification
            cook_success = nimp.sys.process.call(cook_command, heartbeat = 60, simulate = env.simulate)
            if cook_success != 0:
                raise RuntimeError('Cook failed')

        finally:
            if not env.simulate:
                os.remove(configuration_file_path)
                shutil.move(configuration_file_path + '.bak', configuration_file_path)

        nimp.environment.execute_hook('postcook', env)


    @staticmethod
    def stage(env, package_configuration):
        ''' Gather the files required to generate a package '''

        logging.info('Staging package files for %s (Destination: %s)', package_configuration.target_platform, package_configuration.stage_directory)
        logging.info('')

        _try_remove(package_configuration.stage_directory, env.simulate)
        _try_create_directory(package_configuration.stage_directory, env.simulate)

        stage_command = [
            package_configuration.engine_directory + '/Binaries/DotNET/AutomationTool.exe',
            'BuildCookRun', '-UE4exe=UE4Editor-Cmd.exe', '-UTF8Output',
            '-Project=' + package_configuration.project,
            '-TargetPlatform=' + package_configuration.target_platform,
            '-ClientConfig=' + package_configuration.binary_configuration,
            '-SkipCook', '-Stage', '-Pak', '-SkipPak', '-Prereqs', '-CrashReporter', '-NoDebugInfo',
        ]

        stage_success = nimp.sys.process.call(stage_command, simulate = env.simulate)
        if stage_success != 0:
            raise RuntimeError('Stage failed')

        if package_configuration.target_platform == 'XboxOne':
            Package._stage_xbox_manifest(package_configuration, env.simulate)
        Package._stage_layout(package_configuration, env.simulate)

        if package_configuration.package_type in [ 'application', 'application_patch' ]:
            Package._stage_symbols(package_configuration, env.simulate)

        pak_patch_base = '{patch_base_directory}/{project}/Content/Paks'.format(**vars(package_configuration))
        pak_destination_directory = '{stage_directory}/{project}/Content/Paks'.format(**vars(package_configuration))
        for pak_name in package_configuration.pak_collection:
            Package.create_pak_file(env, package_configuration, pak_name, pak_patch_base, pak_destination_directory)

        if package_configuration.target_platform == 'XboxOne':
            if not env.simulate:
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
        pak_file_path = destination + '/' + pak_file_name + ('_P' if package_configuration.package_type == 'application_patch' else '') + '.pak'
        manifest_file_path = destination + '/' + pak_file_name + '.pak.txt'
        order_file_path = package_configuration.project_directory + '/Build/' + package_configuration.cook_platform + '/FileOpenOrder/GameOpenOrder.log'

        if package_configuration.target_platform == 'PS4':
            patch_base = patch_base.lower()
            destination = destination.lower()
            manifest_file_path = manifest_file_path.lower()
            pak_file_path = pak_file_path.lower()

        if not env.simulate:
            os.makedirs(destination, exist_ok = True)

        logging.info('Listing files for pak %s', pak_file_name)
        file_mapper = nimp.system.map_files(env)
        file_mapper.override(pak_name = pak_name).load_set('content_pak')
        all_files = list(file_mapper())

        if (len(all_files) == 0) or (all_files == [(".", None)]):
            logging.warning('No files for %s', pak_file_name)
            return

        # Normalize and sort paths to have a deterministic result across systems
        all_files = sorted((src.replace('\\', '/'), dst.replace('\\', '/')) for src, dst in all_files)

        logging.info('Creating manifest for pak %s', pak_file_name)
        if not env.simulate:
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

        if package_configuration.package_type == 'application_patch':
            pak_command += [ '-GeneratePatch=' + os.path.abspath(patch_base + '/' + pak_file_name + '.pak') ]

        pak_success = nimp.sys.process.call(pak_command, simulate = env.simulate)
        if pak_success != 0:
            raise RuntimeError('Pak creation failed')


    @staticmethod
    def _stage_xbox_manifest(package_configuration, simulate):
        if not simulate:
            os.remove(package_configuration.stage_directory + '/AppxManifest.xml')
            os.remove(package_configuration.stage_directory + '/appdata.bin')

        manifest_source = package_configuration.configuration_directory + '/XboxOne/AppxManifest.xml'
        transform_parameters = {}
        for binary_configuration in package_configuration.binary_configuration.split('+'):
            manifest_destination = 'AppxManifest-%s.xml' % binary_configuration
            transform_parameters['executable_name'] = Package._get_executable_name(package_configuration, binary_configuration)
            transform_parameters['configuration'] = binary_configuration
            Package._stage_and_transform_file(package_configuration.stage_directory, manifest_source, manifest_destination, transform_parameters, simulate)


    @staticmethod
    def _stage_symbols(package_configuration, simulate):
        source = '{project_directory}/Binaries/{target_platform}'.format(**vars(package_configuration))
        destination = '{project}/Binaries/{target_platform}'.format(**vars(package_configuration))

        if package_configuration.target_platform in [ 'Win64', 'XboxOne' ]:
            for binary_configuration in package_configuration.binary_configuration.split('+'):
                pdb_file_name = Package._get_executable_name(package_configuration, binary_configuration) + '.pdb'
                Package._stage_file(package_configuration.stage_directory, source + '/' + pdb_file_name, destination + '/' + pdb_file_name, simulate)


    @staticmethod
    def _stage_layout(package_configuration, simulate):
        if package_configuration.target_platform not in [ 'PS4', 'XboxOne' ]:
            return

        source = package_configuration.layout_file_path
        format_parameters = { 'project': package_configuration.project, 'platform': package_configuration.target_platform }

        if package_configuration.target_platform == 'PS4':
            for title_data in package_configuration.ps4_title_collection:
                transform_parameters = copy.deepcopy(title_data)
                transform_parameters['title_directory'] = transform_parameters['title_directory'].lower()
                for binary_configuration in package_configuration.binary_configuration.split('+'):
                    format_parameters['configuration'] = binary_configuration
                    format_parameters['region'] = title_data['region']
                    destination = '{project}-{region}-{configuration}.gp4'.format(**format_parameters).lower()
                    transform_parameters['executable_name'] = Package._get_executable_name(package_configuration, binary_configuration).lower()
                    transform_parameters['configuration'] = binary_configuration.lower()
                    Package._stage_and_transform_file(package_configuration.stage_directory, source, destination, transform_parameters, simulate)

        elif package_configuration.target_platform == 'XboxOne':
            transform_parameters = {}
            for binary_configuration in package_configuration.binary_configuration.split('+'):
                format_parameters['configuration'] = binary_configuration
                destination = '{project}-{configuration}.xml'.format(**format_parameters)
                transform_parameters['executable_name'] = Package._get_executable_name(package_configuration, binary_configuration)
                transform_parameters['configuration'] = binary_configuration
                Package._stage_and_transform_file(package_configuration.stage_directory, source, destination, transform_parameters, simulate)


    @staticmethod
    def _stage_file(stage_directory, source, destination, simulate):
        logging.info('Staging %s as %s', source, destination)
        if not simulate:
            shutil.copyfile(source, stage_directory + '/' + destination)


    @staticmethod
    def _stage_and_transform_file(stage_directory, source, destination, transform_parameters, simulate):
        logging.info('Staging %s as %s', source, destination)

        with open(source, 'r') as source_file:
            file_content = source_file.read()
        file_content = file_content.format(**transform_parameters)
        if transform_parameters['configuration'].lower() == 'shipping':
            file_content = re.sub(r'<!-- #if Debug -->(.*?)<!-- #endif Debug -->', '', file_content, 0, re.DOTALL)

        if not simulate:
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

        source = package_configuration.stage_directory

        if package_configuration.target_platform in [ 'Linux', 'Mac', 'Win32', 'Win64' ]:
            destination = 'Final' if package_configuration.is_final_submission else 'Default'
            destination = package_configuration.package_directory + '/' + destination
            _try_remove(destination, env.simulate)
            _try_create_directory(destination, env.simulate)

            logging.info('Listing package files')
            package_fileset = nimp.system.map_files(env)
            package_fileset.src(source[ len(env.root_dir) + 1 : ]).to(destination).load_set('stage_to_package')
            all_files = package_fileset()

            for source_file, destination_file in all_files:
                _copy_file(source_file, destination_file, env.simulate)

        elif package_configuration.target_platform == 'PS4':
            package_tool_path = os.path.join(os.environ['SCE_ROOT_DIR'], 'ORBIS', 'Tools', 'Publishing Tools', 'bin', 'orbis-pub-cmd.exe')

            for title_data in package_configuration.ps4_title_collection:
                for binary_configuration in package_configuration.binary_configuration.split('+'):
                    destination = title_data['region'] + '-' + binary_configuration + ('-Final' if package_configuration.is_final_submission else '')
                    destination = package_configuration.package_directory + '/' + destination
                    layout_file = source + '/' + package_configuration.project + '-' + title_data['region'] + '-' + binary_configuration + '.gp4'
                    output_format = 'pkg'
                    if package_configuration.is_final_submission:
                        if package_configuration.package_type == 'application' and title_data['storagetype'].startswith('bd'):
                            output_format += '+iso'
                        output_format += '+subitem'

                    _try_remove(destination, env.simulate)
                    _try_remove(destination + '-Temporary', env.simulate)
                    _try_create_directory(destination, env.simulate)
                    _try_create_directory(destination + '-Temporary', env.simulate)

                    create_package_command = [
                        package_tool_path, 'img_create',
                        '--no_progress_bar',
                        '--tmp_path', destination + '-Temporary',
                        '--oformat', output_format,
                        layout_file, destination
                    ]

                    package_success = nimp.sys.process.call(create_package_command, simulate = env.simulate)
                    if package_success != 0:
                        raise RuntimeError('Package generation failed')

        elif package_configuration.target_platform == 'XboxOne':
            package_tool_path = os.path.join(os.environ['DurangoXDK'], 'bin', 'MakePkg.exe')

            for binary_configuration in package_configuration.binary_configuration.split('+'):
                destination = binary_configuration + ('-Final' if package_configuration.is_final_submission else '')
                destination = package_configuration.package_directory + '/' + destination
                layout_file = source + '/' + package_configuration.project + '-' + binary_configuration + '.xml'
                package_command = [
                    package_tool_path, 'pack', '/v',
                    '/f', layout_file, '/d', source, '/pd', destination,
                    '/productid', package_configuration.xbox_product_id,
                    '/contentid', package_configuration.xbox_content_id,
                ]

                if package_configuration.package_type in [ 'application', 'application_patch' ]:
                    package_command += [ '/genappdata', '/gameos', source + '/era.xvd' ]
                if package_configuration.is_final_submission:
                    package_command += [ '/l' ]

                _try_remove(destination, env.simulate)
                _try_create_directory(destination, env.simulate)

                if not env.simulate:
                    shutil.copyfile(source + '/AppxManifest-%s.xml' % binary_configuration, source + '/AppxManifest.xml')

                package_success = nimp.sys.process.call(package_command, simulate = env.simulate)

                if not env.simulate:
                    os.remove(source + '/AppxManifest.xml')
                    if os.path.isfile(source + '/appdata.bin'):
                        os.remove(source + '/appdata.bin')

                if package_success != 0:
                    raise RuntimeError('Package generation failed')


    @staticmethod
    def verify(env, package_configuration):
        ''' Verify the generated packages '''

        logging.info('Verifying packages (Path: %s)', package_configuration.package_directory)
        logging.info('')

        if package_configuration.target_platform == 'PS4':
            package_tool_path = os.path.join(os.environ['SCE_ROOT_DIR'], 'ORBIS', 'Tools', 'Publishing Tools', 'bin', 'orbis-pub-cmd.exe')

            for title_data in package_configuration.ps4_title_collection:
                for binary_configuration in package_configuration.binary_configuration.split('+'):
                    directory = title_data['region'] + '-' + binary_configuration + ('-Final' if package_configuration.is_final_submission else '')
                    directory = package_configuration.package_directory + '/' + directory

                    _try_remove(directory + '-Temporary', env.simulate)
                    _try_create_directory(directory + '-Temporary', env.simulate)

                    validate_package_command = [
                        package_tool_path, 'img_verify',
                        '--no_progress_bar',
                        '--tmp_path', directory + '-Temporary',
                        '--passcode', title_data['title_passcode'],
                    ]
                    validate_package_command += glob.glob(directory + '/*.pkg')

                    validation_success = nimp.sys.process.call(validate_package_command, simulate = env.simulate)
                    if validation_success != 0:
                        logging.warning('Package validation failed')

                    _try_remove(directory + '-Temporary', env.simulate)

        elif package_configuration.target_platform == 'XboxOne':
            for binary_configuration in package_configuration.binary_configuration.split('+'):
                directory = binary_configuration + ('-Final' if package_configuration.is_final_submission else '')
                directory = package_configuration.package_directory + '/' + directory

                for validator_path in glob.glob(directory + '/Validator_*.xml'):
                    logging.info("Reading %s", validator_path)
                    validator_xml = xml.etree.ElementTree.parse(validator_path).getroot()
                    for test_result in validator_xml.find('testresults').findall('testresult'):
                        for failure in test_result.findall('failure'):
                            logging.error(failure.text)
                        for warning in test_result.findall('warning'):
                            logging.warning(warning.text)
