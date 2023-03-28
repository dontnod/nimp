
import glob
import logging
import os
import re
import subprocess

import nimp.sys.platform

class XSX(nimp.sys.platform.Platform):
    ''' XSX platform description '''

    def __init__(self, env):
        super().__init__(env)
        self.name = 'xsx'
        self.is_microsoft = True

        self.layout_file_extension = 'xml'
        if not os.getenv('UE_SDKS_ROOT'):
            self.package_tool_path = os.path.join(os.getenv('GameDK', default='.'), 'bin', 'MakePkg.exe')

        self.unreal_name = 'XSX'
        self.unreal_config_name = 'XSX'
        self.unreal_cook_name = 'XSX'
        self.unreal_package_directory = '{uproject_dir}/Binaries/XSX'

    def install_package(self, package_directory, env):
        package_glob_pattern = package_directory + '/' + env.unreal_config + '/*.xvc'
        xvcs = glob.glob(package_glob_pattern)
        if not xvcs:
            raise RuntimeError('No xvc file matchin pattern ' + package_glob_pattern)
        if len(xvcs) != 1:
            logging.info('Found xvcs:')
            for xvc in xvcs:
                logging.info('\t\t' + xvc)
            raise RuntimeError('Multiple xvc files matching pattern ' + package_glob_pattern)

        args = [ 'install', xvcs[0] ]
        if env.device:
            args.append('/X:' + env.device)
        return XSX.xbapp(args, env.dry_run)

    def launch_package(self, package_name, env):
        if not package_name:
            package_name = self.get_package_name_from_ini(env.uproject_dir, env.variant)

        installed_packages = self.get_installed_packages(env.device)
        package_name = self.pick_package(installed_packages, package_name, env.unreal_config)

        args = [ 'launch', package_name ]
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
            if not package_name in candidate:
                continue
            if not configuration in candidate:
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
            ini_file_path = '{project_directory}/Config/Variants/{variant}/DefaultGame.ini'.format(**locals())
        else:
            ini_file_path = '{project_directory}/Config/DefaultGame.ini'.format(**locals())
        with open(ini_file_path) as ini_file:
            ini_content = ini_file.read()
        return re.search(r'ProjectName=(.*)', ini_content, re.MULTILINE).group(1)

    def find_gdk():
        # if os.getenv('UE_SDKS_ROOT'):
        #     raise RuntimeError('You seem to be using AutoSDK, which is not supported yet')
        gdk = os.getenv('GameDK')
        if gdk:
            return gdk
        return 'C:\\Program Files (x86)\\Microsoft GDK'

    GDK = find_gdk()
    KIT_PROFILE_PATH = 'Externals\\XboxOne\\Profiles'
    KIT_PROFILE_README = KIT_PROFILE_PATH + '\\readme.md'
    KIT_XBCONFIG_RE = re.compile(r'\w+:\s*([a-zA-Z0-9_-]+)', flags=re.IGNORECASE)

    XBAPP = GDK + '\\bin\\xbapp.exe'
    XBCONFIG = GDK + '\\bin\\xbconfig.exe'
    XBCONNECT = GDK + '\\bin\\xbconnect.exe'
    XBREBOOT = GDK + '\\bin\\xbreboot.exe'
    XBRUN = GDK + '\\bin\\xbrun.exe'
    MAKEPKG = GDK + '\\bin\\MakePkg.exe'
    SIDELOAD = GDK + '\\180702\\sideload'

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
            raise(ValueError('invalid xbox kit ip address'))

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

        raise(ValueError('invalid xbox kit console type'))

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
