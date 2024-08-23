import nimp.sys.platform


class IOS(nimp.sys.platform.Platform):
    '''IOS platform description'''

    def __init__(self, env):
        super().__init__(env)

        self.name = 'ios'
        self.is_mobile = True

        self.unreal_name = 'IOS'
        self.unreal_config_name = 'IOS'
        self.unreal_cook_name = 'IOS'
