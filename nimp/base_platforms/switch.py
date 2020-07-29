
import nimp.sys.platform

class Switch(nimp.sys.platform.Platform):
    ''' Switch platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'switch'

        self.ue4_name = 'Switch'
        self.ue4_config_name = 'Switch'
        self.ue4_cook_name = 'Switch'
