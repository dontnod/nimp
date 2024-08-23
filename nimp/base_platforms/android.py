import nimp.sys.platform


class Android(nimp.sys.platform.Platform):
    '''Android platform description'''

    def __init__(self, env):
        super().__init__(env)

        self.name = 'android'
        self.is_mobile = True
        self.unreal_name = 'Android'
        self.unreal_config_name = 'Android'
        self.unreal_cook_name = 'Android'
