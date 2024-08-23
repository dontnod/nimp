import glob
import json
import logging
import os
import re
import subprocess

import nimp.sys.platform


class PS5(nimp.sys.platform.Platform):
    '''PS5 platform description'''

    def __init__(self, env):
        super().__init__(env)

        self.name = 'ps5'
        # self.aliases = set(['prospero', 'dpx'])
        self.aliases = set(['prospero'])
        self.is_sony = True

        self.layout_file_extension = 'gp5'
        if not os.getenv('UE_SDKS_ROOT'):
            self.package_tool_path = os.path.join(
                os.getenv('SCE_ROOT_DIR', default='.'),
                'PROSPERO',
                'Tools',
                'Publishing Tools',
                'bin',
                'prospero-pub-cmd.exe',
            )

        self.unreal_name = 'PS5'
        self.unreal_config_name = 'PS5'
        self.unreal_cook_name = 'PS5'
        self.unreal_package_directory = '{uproject_dir}/Saved/Packages/PS5'

    def install_package(self, package_directory, env):
        pkgs = glob.glob(package_directory + '/*' + env.unreal_config + '.pkg')
        if not pkgs:
            raise RuntimeError('No pkg file for configuration ' + env.unreal_config + ' in ' + package_directory)
        if len(pkgs) != 1:
            logging.info('Found pkgs:')
            for pkg in pkgs:
                logging.info('\t\t' + pkg)
            raise RuntimeError('Multiple pkg files in ' + package_directory + ' for configuration ' + env.unreal_config)

        return PS5.prospero_ctrl(['package', 'install', pkgs[0]], env.device, dry_run=env.dry_run)

    def launch_package(self, package_name, env):
        if not package_name:
            package_name = env.game
            title_id = self.get_title_id_from_json(env.uproject_dir, env.variant)

        if not title_id:
            installed_titles = self.get_installed_titles(env.device)
            title_id = self.pick_title_id(installed_titles, package_name)

        return PS5.prospero_run(['-app', title_id], env.device, dry_run=env.dry_run)

    _TITLE_ID_RE = re.compile(r'- TitleId: (.*)')
    _TITLE_NAME_RE = re.compile(r'  TitleName: (.*)')

    def get_installed_titles(self, device_ip):
        cmdline = PS5.PROSPERO_CTRL + ' package list'
        if device_ip:
            cmdline += ' /target:' + device_ip
        status, output = subprocess.getstatusoutput(cmdline)
        if status != 0:
            raise RuntimeError('Failed to get list of packages')

        last_title_id = None
        installed_titles = {}
        for line in output.split('\n'):
            m = PS5._TITLE_ID_RE.match(line)
            if m:
                last_title_id = m.group(1)
                continue

            m = PS5._TITLE_NAME_RE.match(line)
            if not m:
                continue

            title_name = m.group(1)
            if not last_title_id:
                raise RuntimeError('Parsing error: missing TitleId before TitleName')
            installed_titles[title_name] = last_title_id
            last_title_id = None

        return installed_titles

    def pick_title_id(self, installed_titles, package_name):
        matching_title_ids = []
        for title_name, title_id in installed_titles.items():
            if package_name in title_name:
                matching_title_ids.append(title_id)

        if len(matching_title_ids) == 1:
            return matching_title_ids[0]

        logging.info("Installed packages:")
        for title_name in installed_titles.keys():
            logging.info("\t\t" + title_name)
        if not matching_title_ids:
            raise RuntimeError('Package ' + package_name + ' not found')
        else:
            raise RuntimeError('Multiple packages found for ' + package_name)

    _CONTENT_ID_RE = re.compile(r'[A-Z]{2}[0-9]{4}-([A-Z]{4}[0-9]{5})_00-[A-Z0-9]{16}')

    def get_title_id_from_json(self, project_directory, variant):
        if variant:
            json_file_path = project_directory + '/Platforms/PS5/Build/Variants/' + variant + '/TitleConfiguration.json'
        else:
            # We allow to launch without --variant for convenience, and expect a BaseGame variant to exist.
            json_file_path = project_directory + '/Platforms/PS5/Build/Variants/BaseGame/TitleConfiguration.json'
            if os.path.exists(json_file_path):
                logging.info(f'No variant specified, using {json_file_path} by default.')
            else:
                logging.warning('No variant specified, no BaseGame variant found.')

        if not os.path.exists(json_file_path):
            return None
        with open(json_file_path) as json_file:
            json_content = json.load(json_file)
        if 'DefaultContentID' not in json_content:
            logging.warning(
                'No "DefaultContentID" attribute found in ' + json_file_path + '. Looking for package name instead.'
            )
            return None

        content_id = json_content['DefaultContentID']  # Use the same content ID as UE4's PS5TitleConfig.cs
        m = PS5._CONTENT_ID_RE.match(content_id)
        if not m:
            logging.warning(
                '"DefaultContentID" attribute in '
                + json_file_path
                + ' does not match the expected format. Looking for package name instaed.'
            )
            return None

        return m.group(1)

    def find_sdk():
        # if os.getenv('UE_SDKS_ROOT'):
        #     raise RuntimeError('You seem to be using AutoSDK, which is not supported yet')
        sdk = os.getenv('SCE_PROSPERO_SDK_DIR')
        if sdk:
            return sdk
        return 'C:\\Program Files (x86)\\SCE\\Prospero SDKs\\2.000'

    SDK = find_sdk()
    TOOLS_BIN_DIR = SDK + '\\..\\..\\Prospero\\Tools\\Target Manager Server\\bin'
    PROSPERO_CTRL = TOOLS_BIN_DIR + '\\prospero-ctrl.exe'
    PROSPERO_RUN = TOOLS_BIN_DIR + '\\prospero-run.exe'

    @staticmethod
    def prospero_ctrl(args, ip=None, dry_run=False):
        if ip:
            args.append('/target:' + ip)
        cmdline = [PS5.PROSPERO_CTRL] + args
        logging.info('Running %s', cmdline)
        if dry_run:
            return True
        result = subprocess.call(
            cmdline
        )  # Call subprocess directly to allow "dynamic" output (with progress percentage)
        return result == 0

    @staticmethod
    def prospero_run(args, ip=None, dry_run=False):
        if ip:
            args = ['/target:' + ip] + args  # "/target" needs to be before "/app"
        result = nimp.sys.process.call([PS5.PROSPERO_RUN] + args, dry_run=dry_run)
        return result == 0
