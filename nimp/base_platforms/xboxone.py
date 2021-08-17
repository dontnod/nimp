
import os
import nimp.sys.platform

class XboxOne(nimp.sys.platform.Platform):
    ''' XboxOne platform description '''

    def __init__(self, env):
        super().__init__(env)

        xdk_root = os.environ.get('DurangoXDK', None) or '/'

        self.name = 'xboxone'
        self.is_microsoft = True

        self.layout_file_extension = 'xml'
        self.package_tool_path = os.path.join(os.getenv('DurangoXDK', default='.'), 'bin', 'MakePkg.exe')

        self.unreal_name = 'XboxOne'
        self.unreal_config_name = 'XboxOne'
        self.unreal_cook_name = 'XboxOne'
