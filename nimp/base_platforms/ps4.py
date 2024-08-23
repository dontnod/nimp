import os

import nimp.sys.platform


class PS4(nimp.sys.platform.Platform):
    '''PS4 platform description'''

    def __init__(self, env):
        super().__init__(env)

        sce_root = os.getenv('SCE_ROOT_DIR', default='.')

        self.name = 'ps4'
        self.aliases = set(['orbis'])
        self.is_sony = True

        self.layout_file_extension = 'gp4'
        self.package_tool_path = os.path.join(
            sce_root, 'ORBIS', 'Tools', 'Publishing Tools', 'bin', 'orbis-pub-cmd.exe'
        )

        self.unreal_name = 'PS4'
        self.unreal_config_name = 'PS4'
        self.unreal_cook_name = 'PS4'
