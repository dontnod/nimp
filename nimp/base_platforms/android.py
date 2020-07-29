
import nimp.sys.platform

class Android(nimp.sys.platform.Platform):
    ''' Android platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'android'
        self.is_mobile = True
        self.ue4_name = 'Android'
        self.ue4_config_name = 'Android'
        self.ue4_cook_name = 'Android'
