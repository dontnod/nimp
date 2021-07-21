
import os

import nimp.sys.platform

class Switch(nimp.sys.platform.Platform):
    ''' Switch platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'switch'

        self.unreal_name = 'Switch'
        self.unreal_config_name = 'Switch'
        self.unreal_cook_name = 'Switch'

        self.is_nintendo = True

        self.unreal_package_directory = '{uproject_dir}/Binaries/Switch'
