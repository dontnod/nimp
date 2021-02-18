
import os

import nimp.sys.platform

class Switch(nimp.sys.platform.Platform):
    ''' Switch platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'switch'

        self.ue4_name = 'Switch'
        self.ue4_config_name = 'Switch'
        self.ue4_cook_name = 'Switch'

        self.is_nintendo = True

        self.ue4_package_directory = '{uproject_dir}/Binaries/Switch'
