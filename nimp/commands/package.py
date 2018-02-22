# -*- coding: utf-8 -*-
# Copyright © 2014—2018 Dontnod Entertainment

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

import logging
import os
import re
import shutil
import time
import xml.etree.ElementTree

import nimp.commands
import nimp.environment
import nimp.system
import nimp.sys.process


def _get_ini_value(file_path, key):
    ''' Retrieves a value from a ini file '''
    file_path = nimp.system.sanitize_path(file_path)
    with open(file_path) as ini_file:
        ini_content = ini_file.read()
    match = re.search('^' + key + r'=(?P<value>.*?)$', ini_content, re.MULTILINE)
    if not match:
        raise KeyError('Key {key} was not found in {file_path}'.format(**locals()))
    return match.group('value')


def _get_sfo_data(project_directory, title_id):
    ''' Retrieves data from a sfo file '''
    orbis_tool_path = nimp.system.sanitize_path(os.environ['SCE_ROOT_DIR'] + '/ORBIS/Tools/Publishing Tools/bin/orbis-pub-cmd.exe')
    sfo_file_path = project_directory + '/Saved/StagedBuilds/PS4/sce_sys/' + title_id + '/param.sfo'
    sfx_file_path = sfo_file_path.replace('/param.sfo', '/param.sfx')
    sfo_export_command = [ orbis_tool_path, 'sfo_export', sfo_file_path, sfx_file_path ]

    sfo_export_success = nimp.sys.process.call(sfo_export_command)
    if sfo_export_success != 0:
        raise RuntimeError('Failed to export sfo data from {sfo_file_path}'.format(**locals()))

    sfx_data = {}
    for sfx_param in xml.etree.ElementTree.parse(sfx_file_path).getroot():
        sfx_data[sfx_param.attrib['key']] = sfx_param.text
    os.remove(sfx_file_path)
    return sfx_data


def _safe_remove(file_path):
    attempt_maximum = 5
    attempt = 1

    logging.info('Removing %s', file_path)
    while attempt <= attempt_maximum:
        try:
            if os.path.exists(file_path):
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
            break
        except OSError as exception:
            logging.warning('%s (Attempt %s of %s)', exception, attempt, attempt_maximum)
            if attempt >= attempt_maximum:
                raise exception
            time.sleep(10)
            attempt += 1


class Package(nimp.command.Command):
    ''' Packages an unreal project for release '''
    def __init__(self):
        super(Package, self).__init__()


    def configure_arguments(self, env, parser):
        nimp.command.add_common_arguments(parser, 'configuration', 'platform', 'revision')

        command_steps = [ 'initialize', 'precook', 'cook', 'postcook', 'prestage', 'stage', 'package' ]
        parser.add_argument('--steps', help = 'Only run specified steps instead of all of them',
                            choices = command_steps, default = command_steps, nargs = '+')
        parser.add_argument('--target', help = 'Set the target configuration to use')
        parser.add_argument('--layout', help = 'Set the layout file to use for the package (for consoles)')
        parser.add_argument('--patch', help = 'Create a patch based on the specified release', metavar = '<version>')
        parser.add_argument('--final', help = 'Enable package options for final submission', action = 'store_true')
        parser.add_argument('--iterate', help = 'Enable iterative cooking', action = 'store_true')
        parser.add_argument('--compress', help = 'Enable pak file compression', action = 'store_true')

        return True


    def is_available(self, env):
        return nimp.unreal.is_unreal4_available(env)


    def run(self, env):
        ue4_cmd_platform = {'Win64': 'WindowsNoEditor', 'Linux': 'LinuxNoEditor'}.get(env.ue4_platform, env.ue4_platform)
        engine_directory = env.format('{root_dir}/Engine')
        project_directory = env.format('{root_dir}/{game}')
        stage_directory = env.format('{root_dir}/{game}/Saved/StagedBuilds/' + ue4_cmd_platform)
        package_directory = env.format('{root_dir}/{game}/Saved/Packages/' + ue4_cmd_platform)

        if 'initialize' in env.steps:
            Package._initialize(env)
        if 'cook' in env.steps:
            Package._cook(engine_directory, env.game, ue4_cmd_platform, env.iterate)
        if 'postcook' in env.steps:
            Package._postcook(env)
        if 'prestage' in env.steps:
            Package._postcook(env)
        if 'stage' in env.steps:
            Package._stage(env, engine_directory, project_directory, stage_directory,
                env.game, env.ue4_platform, env.ue4_config,
                env.content_paks, env.layout, env.compress, env.patch)
        if 'package' in env.steps:
            Package._package_for_platform(env, project_directory, env.game, env.ue4_platform, env.ue4_config, stage_directory, package_directory, env.final)

        return True


    @staticmethod
    def _initialize(env):
        if env.target:
            configuration_fileset = nimp.system.map_files(env)
            configuration_fileset.src('{game}/Config.{target}').to('{root_dir}/{game}/Config').glob('**')
            configuration_success = nimp.system.all_map(nimp.system.robocopy, configuration_fileset())
            if not configuration_success:
                raise RuntimeError('Initialize failed')

        # Deprecated hook name
        hook_success = nimp.environment.execute_hook('preship', env)
        if not hook_success:
            raise RuntimeError('Initialize failed')

        hook_success = nimp.environment.execute_hook('precook', env)
        if not hook_success:
            raise RuntimeError('Initialize failed')


    @staticmethod
    def _cook(engine_directory, project, platform, iterate):
        editor = 'Linux/UE4Editor' if platform == 'LinuxNoEditor' else 'Win64/UE4Editor-Cmd.exe'
        cook_command = [
            nimp.system.sanitize_path(engine_directory + '/Binaries/' + editor),
            project, '-Run=Cook', '-TargetPlatform=' + platform,
            '-BuildMachine', '-Unattended', '-StdOut', '-UTF8Output',
        ]
        if iterate:
            cook_command += [ '-Iterate', '-IterateHash' ]

        # Heartbeart for background shader compilation and existing cook verification
        cook_success = nimp.sys.process.call(cook_command, heartbeat = 60)
        if cook_success != 0:
            raise RuntimeError('Cook failed')


    @staticmethod
    def _postcook(env):
        hook_success = nimp.environment.execute_hook('postcook', env)
        if not hook_success:
            raise RuntimeError('Post-cook failed')

        # Deprecated hook name
        hook_success = nimp.environment.execute_hook('prestage', env)
        if not hook_success:
            raise RuntimeError('Pre-stage failed')


    @staticmethod
    def _stage(env, engine_directory, project_directory, stage_directory, project, platform, configuration, content_pak_list, layout_file_path, compress, patch):
        stage_directory = nimp.system.sanitize_path(stage_directory)

        _safe_remove(stage_directory)
        os.makedirs(stage_directory)

        stage_command = [
            nimp.system.sanitize_path(engine_directory + '/Binaries/DotNET/AutomationTool.exe'),
            'BuildCookRun', '-UE4exe=UE4Editor-Cmd.exe', '-UTF8Output',
            '-Project=' + project, '-TargetPlatform=' + platform, '-ClientConfig=' + configuration,
            '-SkipCook', '-Stage', '-Pak', '-SkipPak', '-Prereqs', '-CrashReporter', '-NoDebugInfo',
        ]
        if compress:
            stage_command += [ '-Compressed' ]
        if patch:
            stage_command += [ '-GeneratePatch', '-BasedOnReleaseVersion=' + patch ]

        stage_success = nimp.sys.process.call(stage_command)
        if stage_success != 0:
            raise RuntimeError('Stage failed')

        pak_destination_directory = '{stage_directory}/{project}/Content/Paks'.format(**locals())
        if platform == 'PS4':
            pak_destination_directory = pak_destination_directory.lower()
        os.makedirs(pak_destination_directory)
        for content_pak in content_pak_list:
            Package._create_pak_file(env, engine_directory, project_directory, project, platform, content_pak, pak_destination_directory, compress, patch)

        if platform == 'XboxOne':
            Package._stage_xbox_manifest(project_directory, stage_directory, configuration)
            # Dummy files for empty chunks
            with open(nimp.system.sanitize_path(stage_directory + '/LaunchChunk.bin'), 'w') as empty_file:
                empty_file.write('\0')
            with open(nimp.system.sanitize_path(stage_directory + '/AlignmentChunk.bin'), 'w') as empty_file:
                empty_file.write('\0')

        if layout_file_path:
            for current_configuration in configuration.split('+'):
                layout_file_name = project + '-' + current_configuration + '.' + ('gp4' if platform == 'PS4' else 'xml')
                layout_destination = nimp.system.sanitize_path(stage_directory + '/' + layout_file_name)
                Package._stage_file(layout_file_path, layout_destination, True, platform, current_configuration)

        # Homogenize binary and symbols file names for console packaging
        if platform == 'PS4':
            binary_path = nimp.system.sanitize_path(stage_directory + '/' + (project + '/Binaries/PS4/' + project).lower() + '.self')
            if os.path.exists(binary_path):
                shutil.move(binary_path, binary_path.replace(project.lower() + '.self', project.lower() + '-ps4-development.self'))
        elif platform == 'XboxOne':
            binary_path = nimp.system.sanitize_path(stage_directory + '/' + project + '/Binaries/XboxOne/' + project + '.exe')
            symbols_path = nimp.system.sanitize_path(stage_directory + '/Symbols/' + project + '-symbols.bin')
            if os.path.exists(binary_path):
                shutil.move(binary_path, binary_path.replace(project + '.exe', project + '-XboxOne-Development.exe'))
            if os.path.exists(symbols_path):
                shutil.move(symbols_path, symbols_path.replace(project + '-symbols.bin', project + '-XboxOne-Development-symbols.bin'))

        # Copy the release files to have a complete package
        if patch:
            ue4_cmd_platform = {'Win64': 'WindowsNoEditor', 'Linux': 'LinuxNoEditor'}.get(platform, platform)
            release_directory = project_directory + '/Releases/' + patch + '/' + ue4_cmd_platform
            pak_file_name = project + '-' + ue4_cmd_platform + '.pak'
            Package._stage_file(release_directory + '/' + pak_file_name, stage_directory + '/' + project + '/Content/Paks/' + pak_file_name)


    @staticmethod
    def _create_pak_file(env, engine_directory, project_directory, project, platform, pak_name, destination, compress, patch):
        pak_tool = 'Linux/UnrealPak' if platform == 'Linux' else 'Win64/UnrealPak.exe'
        pak_tool_path = nimp.system.sanitize_path(engine_directory + '/Binaries/' + pak_tool)
        ue4_cmd_platform = {'Win64': 'WindowsNoEditor', 'Linux': 'LinuxNoEditor'}.get(platform, platform)
        pak_file_name = project + '-' + ue4_cmd_platform + (('-' + pak_name) if pak_name else '') + ('_P' if patch else '') + '.pak'
        manifest_file_path = nimp.system.sanitize_path(destination + '/' + pak_file_name + '.txt')
        order_file_path = nimp.system.sanitize_path(project_directory + '/Build/' + ue4_cmd_platform + '/FileOpenOrder/GameOpenOrder.log')
        pak_file_path = nimp.system.sanitize_path(destination + '/' + pak_file_name)

        if platform == 'PS4':
            manifest_file_path = manifest_file_path.lower()
            pak_file_path = pak_file_path.lower()

        logging.info('Listing files for %s', pak_file_name)
        file_mapper = nimp.system.map_files(env)
        file_mapper.override(pak_name = pak_name).load_set('content_pak')
        with open(manifest_file_path, 'w') as manifest_file:
            for src, dst in sorted(file_mapper()):
                manifest_file.write('"%s" "%s"\n' % (os.path.abspath(src), '../../../' + dst))

        pak_command = [
            pak_tool_path, os.path.abspath(pak_file_path),
            '-Create=' + os.path.abspath(manifest_file_path),
            '-Order=' + os.path.abspath(order_file_path),
        ]

        if compress:
            pak_command += [ '-Compress' ]

        if platform == 'Win64':
            pak_command += [ '-PatchPaddingAlign=2048' ]
        elif platform == 'PS4':
            pak_command += [ '-BlockSize=256MB', '-PatchPaddingAlign=65536' ]
        elif platform == 'XboxOne':
            pak_command += [ '-BlockSize=4KB', '-BitWindow=12' ]

        pak_success = nimp.sys.process.call(pak_command)
        if pak_success != 0:
            raise RuntimeError('Pak creation failed')


    @staticmethod
    def _stage_xbox_manifest(project_directory, stage_directory, configuration):
        os.remove(nimp.system.sanitize_path(stage_directory + '/AppxManifest.xml'))
        os.remove(nimp.system.sanitize_path(stage_directory + '/appdata.bin'))

        manifest_source = project_directory + '/Config/XboxOne/AppxManifest.xml'
        for current_configuration in configuration.split('+'):
            current_stage_directory = stage_directory + '/Manifests/' + current_configuration
            os.makedirs(nimp.system.sanitize_path(current_stage_directory))
            Package._stage_file(manifest_source, current_stage_directory + '/AppxManifest.xml', True, 'XboxOne', current_configuration)

            appdata_command = [
                nimp.system.sanitize_path(os.environ['DurangoXDK'] + '/bin/MakePkg.exe'),
                'appdata',
                '/f', nimp.system.sanitize_path(current_stage_directory +  '/AppxManifest.xml'),
                '/pd', nimp.system.sanitize_path(current_stage_directory),
            ]

            appdata_success = nimp.sys.process.call(appdata_command)
            if appdata_success != 0:
                raise RuntimeError('Stage failed')


    @staticmethod
    def _stage_file(source, destination, apply_transform = False, platform = None, configuration = None):
        source = nimp.system.sanitize_path(source)
        destination = nimp.system.sanitize_path(destination)
        logging.info('Staging %s to %s', source, destination)

        if apply_transform:
            with open(source, 'r') as source_file:
                file_content = source_file.read()
            file_content = file_content.format(configuration = (configuration if platform != 'PS4' else configuration.lower()))
            if configuration == 'Shipping':
                file_content = re.sub(r'<!-- #if Debug -->(.*?)<!-- #endif Debug -->', '', file_content, 0, re.DOTALL)
            with open(destination, 'w') as destination_file:
                destination_file.write(file_content)
        else:
            shutil.copyfile(source, destination)


    @staticmethod
    def _package_for_platform(env, project_directory, project, platform, configuration, source, destination, is_final_submission):
        source = nimp.system.sanitize_path(source)
        destination = nimp.system.sanitize_path(destination)

        _safe_remove(destination)
        os.makedirs(destination)

        if platform in [ 'Linux', 'Mac', 'Win32', 'Win64' ]:
            package_fileset = nimp.system.map_files(env)
            package_fileset.src(source[ len(env.root_dir) + 1 : ]).to(destination).glob('**')
            package_success = nimp.system.all_map(nimp.system.robocopy, package_fileset())
            if not package_success:
                raise RuntimeError('Package failed')

        elif platform == 'XboxOne':
            package_tool_path = nimp.system.sanitize_path(os.environ['DurangoXDK'] + '/bin/MakePkg.exe')
            game_os = nimp.system.sanitize_path(source + '/era.xvd')
            ini_file_path = nimp.system.sanitize_path(project_directory + '/Config/XboxOne/XboxOneEngine.ini')
            product_id = _get_ini_value(ini_file_path, 'ProductId')
            content_id = _get_ini_value(ini_file_path, 'ContentId')
            symbol_path = nimp.system.sanitize_path(project_directory + '/Binaries/XboxOne')

            for current_configuration in configuration.split('+'):
                current_destination = nimp.system.sanitize_path(destination + '/' + current_configuration)
                layout_file = nimp.system.sanitize_path(source + '/' + project + '-' + current_configuration + '.xml')
                package_command = [
                    package_tool_path, 'pack', '/v', '/gameos', game_os,
                    '/f', layout_file, '/d', source, '/pd', current_destination,
                    '/productid', product_id, '/contentid', content_id,
                    '/symbolpaths', symbol_path,
                ]

                if is_final_submission:
                    package_command += [ '/l' ]

                os.mkdir(current_destination)
                manifest_file_collection = os.listdir(nimp.system.sanitize_path(source + '/Manifests/' + current_configuration))
                for manifest_file in manifest_file_collection:
                    shutil.copyfile(nimp.system.sanitize_path(source + '/Manifests/' + current_configuration + '/' + manifest_file),
                                    nimp.system.sanitize_path(source + '/' + manifest_file))
                package_success = nimp.sys.process.call(package_command)
                for manifest_file in manifest_file_collection:
                    os.remove(nimp.system.sanitize_path(source + '/' + manifest_file))
                if package_success != 0:
                    raise RuntimeError('Package failed')

        elif platform == 'PS4':
            package_tool_path = nimp.system.sanitize_path(os.environ['SCE_ROOT_DIR'] + '/ORBIS/Tools/Publishing Tools/bin/orbis-pub-cmd.exe')
            temporary_directory = nimp.system.sanitize_path(project_directory + '/Saved/Temp')
            os.makedirs(temporary_directory, exist_ok = True)
            ini_file_path = project_directory + '/Config/PS4/PS4Engine.ini'
            title_id = _get_ini_value(ini_file_path, 'TitleID')
            title_passcode = _get_ini_value(ini_file_path, 'TitlePasscode')
            sfo_data = _get_sfo_data(project_directory, title_id)

            for current_configuration in configuration.split('+'):
                current_destination = nimp.system.sanitize_path(destination + '/' + current_configuration)
                destination_file = '{content_id}-A{application_version}-V{master_version}.pkg'.format(
                    content_id = sfo_data['CONTENT_ID'],
                    application_version = sfo_data['APP_VER'].replace('.', ''),
                    master_version = sfo_data['VERSION'].replace('.', '')
                )
                destination_file = nimp.system.sanitize_path(current_destination + '/' + destination_file)
                layout_file = nimp.system.sanitize_path(source + '/' + project + '-' + current_configuration + '.gp4')
                create_package_command = [
                    package_tool_path, 'img_create',
                    '--no_progress_bar',
                    '--tmp_path', temporary_directory,
                    layout_file, destination_file
                ]

                os.mkdir(current_destination)
                package_success = nimp.sys.process.call(create_package_command)
                if package_success != 0:
                    raise RuntimeError('Package failed')

                if current_configuration == 'Shipping':
                    verify_package_command = [
                        package_tool_path, 'img_verify',
                        '--no_progress_bar',
                        '--tmp_path', temporary_directory,
                        '--passcode', title_passcode, destination_file
                    ]
                    package_success = nimp.sys.process.call(verify_package_command)
                    if package_success != 0:
                        raise RuntimeError('Package failed')

