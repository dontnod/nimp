
import nimp.sys.platform

class IOS(nimp.sys.platform.Platform):
    ''' IOS platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'ios'
        self.is_mobile = True

        self.ue4_name = 'IOS'
        self.ue4_config_name = 'IOS'
        self.ue4_cook_name = 'IOS'
