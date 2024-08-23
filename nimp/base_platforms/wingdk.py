import glob
import logging

from nimp.base_platforms.basegdk import BaseGDK
import nimp.sys.process


class WinGDK(BaseGDK):
    '''WinGDK platform description'''

    def __init__(self, env):
        super().__init__(env)
        self.name = 'wingdk'
        self.unreal_name = 'WinGDK'
        self.unreal_config_name = 'WinGDK'
        self.unreal_cook_name = 'WinGDK'

    def install_package(self, package_directory, env):
        msixvcs = glob.glob(package_directory + '/*.msixvc')
        if not msixvcs:
            raise RuntimeError('No msixvc file in ' + package_directory)
        if len(msixvcs) != 1:
            logging.info('Found msixvc:')
            for msixvc in msixvcs:
                logging.info('\t\t' + msixvc)
            raise RuntimeError('Multiple msixvc files in ' + package_directory)

        args = ['install', msixvcs[0]]

        return WinGDK.wdapp(args, env.dry_run)

    WDAPP = BaseGDK.GDK + '\\bin\\wdapp.exe'

    @staticmethod
    def wdapp(args, dry_run=False):
        result = nimp.sys.process.call([WinGDK.WDAPP] + args, dry_run=dry_run)
        return result == 0
