
import os
import nimp.sys.platform

class XboxOne(nimp.sys.platform.Platform):
    ''' XboxOne platform description '''

    def __init__(self):
        super().__init__()

        xdk_root = os.environ.get('DurangoXDK', None) or '/'

        self.name = 'xboxone'
        self.is_microsoft = True

        self.layout_file_extension = 'xml'
        if not os.getenv('UE_SDKS_ROOT'):
            self.package_tool_path = os.path.join(os.environ['DurangoXDK'], 'bin', 'MakePkg.exe')

        self.ue4_name = 'XboxOne'
        self.ue4_config_name = 'XboxOne'
        self.ue4_cook_name = 'XboxOne'
