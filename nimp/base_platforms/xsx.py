import glob
import logging
import os
import re
import subprocess

from nimp.base_platforms.basegdk import BaseGDK
import nimp.sys.process


class XSX(BaseGDK):
    '''XSX platform description'''

    def __init__(self, env):
        super().__init__(env)
        self.name = 'xsx'

        self.unreal_name = 'XSX'
        self.unreal_config_name = 'XSX'
        self.unreal_cook_name = 'XSX'
        self.unreal_package_directory = '{uproject_dir}/Binaries/XSX'

    def install_package(self, package_directory, env):
        xvcs = glob.glob(package_directory + '/*.xvc')
        if not xvcs:
            raise RuntimeError('No xvc file in ' + package_directory)
        if len(xvcs) != 1:
            logging.info('Found xvcs:')
            for xvc in xvcs:
                logging.info('\t\t' + xvc)
            raise RuntimeError('Multiple xvc files in ' + package_directory)

        args = ['install', xvcs[0]]
        if env.device:
            args.append('/X:' + env.device)
        return XSX.xbapp(args, env.dry_run)

    def launch_package(self, package_name, env):
        if not package_name:
            package_name = self.get_package_name_from_ini(env.uproject_dir, env.variant)

        installed_packages = self.get_installed_packages(env.device)
        package_name = self.pick_package(installed_packages, package_name, env.unreal_config)

        args = ['launch', package_name]
        if env.device:
            args.append('/X:' + env.device)
        return XSX.xbapp(args, env.dry_run)

    _PACKAGE_NAME_RE = re.compile(r'        (\S+)$')

    def get_installed_packages(self, device_ip):
        cmdline = '"' + XSX.XBAPP + '" list'
        if device_ip:
            cmdline += ' /x:' + device_ip
        status, output = subprocess.getstatusoutput(cmdline)
        if status != 0:
            raise RuntimeError('Failed to get list of packages')

        installed_packages = []
        for line in output.split('\n'):
            m = XSX._PACKAGE_NAME_RE.match(line)
            if not m:
                continue
            installed_packages.append(m.group(1))

        return installed_packages

    def pick_package(self, installed_packages, package_name, configuration):
        matching_packages = []
        for candidate in installed_packages:
            if package_name not in candidate:
                continue
            if configuration not in candidate:
                continue
            matching_packages.append(candidate)

        if len(matching_packages) == 1:
            return matching_packages[0]

        logging.info('Installed packages:')
        for pkg in installed_packages:
            logging.info('\t\t' + pkg)
        if not matching_packages:
            raise RuntimeError('Package ' + package_name + ' not found for configuration ' + configuration)
        else:
            raise RuntimeError('Multiple packages found for ' + package_name + ' for configuration ' + configuration)

    def get_package_name_from_ini(self, project_directory, variant):
        if variant:
            ini_file_path = f'{project_directory}/Config/Variants/{variant}/DefaultGame.ini'
        else:
            ini_file_path = f'{project_directory}/Config/DefaultGame.ini'
        logging.info('Search for ProjectName in "%s"', ini_file_path)
        with open(ini_file_path, encoding='utf-8') as ini_file:
            ini_content = ini_file.read()
        return re.search(r'ProjectName=(.*)', ini_content, re.MULTILINE).group(1)

    KIT_PROFILE_PATH = 'Externals\\XboxOne\\Profiles'
    KIT_PROFILE_README = KIT_PROFILE_PATH + '\\readme.md'
    KIT_XBCONFIG_RE = re.compile(r'\w+:\s*([a-zA-Z0-9_-]+)', flags=re.IGNORECASE)

    XBAPP = BaseGDK.GDK + '\\bin\\xbapp.exe'
    XBCONFIG = BaseGDK.GDK + '\\bin\\xbconfig.exe'
    XBCONNECT = BaseGDK.GDK + '\\bin\\xbconnect.exe'
    XBREBOOT = BaseGDK.GDK + '\\bin\\xbreboot.exe'
    XBRUN = BaseGDK.GDK + '\\bin\\xbrun.exe'
    MAKEPKG = BaseGDK.GDK + '\\bin\\MakePkg.exe'
    SIDELOAD = BaseGDK.GDK + '\\180702\\sideload'

    @staticmethod
    def xbapp(args, dry_run=False):
        result = nimp.sys.process.call([XSX.XBAPP] + args, dry_run=dry_run)
        return result == 0

    @staticmethod
    def xbconfig(args, dry_run=False):
        result = nimp.sys.process.call([XSX.XBCONFIG] + args, dry_run=dry_run)
        return result == 0

    @staticmethod
    def xbconnect(ip, dry_run=False):
        result = nimp.sys.process.call([XSX.XBCONNECT, ip], dry_run=dry_run)
        return result == 0

    @staticmethod
    def xbreboot(dry_run=False):
        result = nimp.sys.process.call([XSX.XBREBOOT], dry_run=dry_run)
        return result == 0

    @staticmethod
    def xbrun(args, dry_run=False):
        result = nimp.sys.process.call([XSX.XBRUN] + args, dry_run=dry_run)
        return result == 0

    @staticmethod
    def makepkg(args, dry_run=False):
        result = nimp.sys.process.call([XSX.MAKEPKG] + args, dry_run=dry_run)
        return result == 0

    @staticmethod
    def defaultkit_ip():
        logging.info(XSX.XBCONNECT + ' /Q /B')
        status, output = subprocess.getstatusoutput('"' + XSX.XBCONNECT + '" /Q /B')
        if status != 0:
            raise (ValueError('invalid xbox kit ip address'))

        return output

    @staticmethod
    def kit_profile_fname(root_dir, consoleType, config):
        profiles_dir = os.path.join(root_dir, XSX.KIT_PROFILE_PATH, consoleType)
        if not os.path.isdir(profiles_dir):
            logging.error('unknown xbox console type : ' + consoleType)
            return None

        profile_fname = os.path.join(profiles_dir, config + '.txt')
        profile_fname = os.path.abspath(profile_fname)

        if not os.path.isfile(profile_fname):
            logging.error('unknown xbox kit profile : ' + profile_fname)
            return None

        return profile_fname

    @staticmethod
    def kit_console_type():
        logging.info(XSX.XBCONFIG + ' ConsoleType')
        status, output = subprocess.getstatusoutput('"' + XSX.XBCONFIG + '" ConsoleType')
        if status == 0:
            output = output.strip()
            m = XSX.KIT_XBCONFIG_RE.match(output)
            if m:
                return str(m.group(1))

        raise (ValueError('invalid xbox kit console type'))

    @staticmethod
    def kit_console_name(kit):
        logging.info(XSX.XBCONFIG + ' hostname /X ' + kit)
        status, output = subprocess.getstatusoutput('"' + XSX.XBCONFIG + '" hostname /X ' + kit)
        if status == 0:
            output = output.strip()
            m = XSX.KIT_XBCONFIG_RE.match(output)
            if m:
                return str(m.group(1))

        raise (ValueError('invalid xbox kit console type'))
