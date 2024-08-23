import nimp.sys.platform


class Win32(nimp.sys.platform.Platform):
    '''Win32 platform description'''

    def __init__(self, env):
        super().__init__(env)

        self.name = 'win32'
        self.aliases = set(['pcconsole'])
        self.is_microsoft = True

        self.unreal_name = 'Win32'
        self.unreal_config_name = 'Windows'
        if env.is_ue5:
            self.unreal_cook_name = 'Windows'
        else:
            self.unreal_cook_name = 'WindowsNoEditor'


class Win64(nimp.sys.platform.Platform):
    '''Win64 platform description'''

    def __init__(self, env):
        super().__init__(env)

        self.name = 'win64'
        self.aliases = set(['pc', 'windows'])
        self.is_microsoft = True

        self.unreal_name = 'Win64'
        self.unreal_config_name = 'Windows'
        if env.is_ue5:
            self.unreal_cook_name = 'Windows'
        else:
            self.unreal_cook_name = 'WindowsNoEditor'

    def launch_package(self, package_name, env):
        if not package_name:
            package_name = (
                env.uproject_dir + '/Saved/Packages/' + self.unreal_cook_name + '/Default/' + env.game + '.exe'
            )
        result = nimp.sys.process.call([package_name])
        return result == 0


class Linux(nimp.sys.platform.Platform):
    '''Linux platform description'''

    def __init__(self, env):
        super().__init__(env)

        self.name = 'linux'

        self.unreal_name = 'Linux'
        self.unreal_config_name = 'Linux'
        if env.is_ue5:
            self.unreal_cook_name = 'Linux'
        else:
            self.unreal_cook_name = 'LinuxNoEditor'


class Mac(nimp.sys.platform.Platform):
    '''Mac platform description'''

    def __init__(self, env):
        super().__init__(env)

        self.name = 'mac'
        self.aliases = set(['macos', 'osx'])

        self.unreal_name = 'Mac'
        self.unreal_config_name = 'Mac'
        if env.is_ue5:
            self.unreal_cook_name = 'Mac'
        else:
            self.unreal_cook_name = 'MacNoEditor'
