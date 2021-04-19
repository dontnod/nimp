
import nimp.sys.platform

class Win32(nimp.sys.platform.Platform):
    ''' Win32 platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'win32'
        self.aliases = set(['pcconsole'])
        self.is_microsoft = True

        self.ue4_name = 'Win32'
        self.ue4_config_name = 'Windows'
        self.ue4_cook_name = 'WindowsNoEditor'


class Win64(nimp.sys.platform.Platform):
    ''' Win64 platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'win64'
        self.aliases = set(['pc', 'windows'])
        self.is_microsoft = True

        self.ue4_name = 'Win64'
        self.ue4_config_name = 'Windows'
        self.ue4_cook_name = 'WindowsNoEditor'

    def launch_package(self, package_name, env):
        if not package_name:
            package_name = env.uproject_dir + '/Saved/Packages/WindowsNoEditor/Default/' + env.game + '.exe'
        result = nimp.sys.process.call([ package_name ])
        return result == 0

class Linux(nimp.sys.platform.Platform):
    ''' Linux platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'linux'

        self.ue4_name = 'Linux'
        self.ue4_config_name = 'Linux'
        self.ue4_cook_name = 'LinuxNoEditor'


class Mac(nimp.sys.platform.Platform):
    ''' Mac platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'mac'
        self.aliases = set(['macos', 'osx'])

        self.ue4_name = 'Mac'
        self.ue4_config_name = 'Mac'
        self.ue4_cook_name = 'MacNoEditor'
