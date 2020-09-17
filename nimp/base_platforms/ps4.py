
import os

import nimp.sys.platform

class PS4(nimp.sys.platform.Platform):
    ''' PS4 platform description '''

    def __init__(self):
        super().__init__()

        sce_root = os.environ.get('SCE_ROOT_DIR', None) or '/'

        self.name = 'ps4'
        self.aliases = set(['orbis'])
        self.is_sony = True

        self.layout_file_extension = 'gp4'
        self.package_tool_path = os.path.join(os.getenv('SCE_ROOT_DIR', default='.'), 'ORBIS', 'Tools', 'Publishing Tools', 'bin', 'orbis-pub-cmd.exe')

        self.ue4_name = 'PS4'
        self.ue4_config_name = 'PS4'
        self.ue4_cook_name = 'PS4'
