import nimp.sys.platform
import os


class BaseGDK(nimp.sys.platform.Platform):
    '''BaseGDK platform description'''

    def __init__(self, env):
        super().__init__(env)

        self.is_microsoft = True

        self.layout_file_extension = 'xml'
        if not os.getenv('UE_SDKS_ROOT'):
            self.package_tool_path = os.path.join(os.getenv('GameDK', default='.'), 'bin', 'MakePkg.exe')

    def find_gdk():
        # if os.getenv('UE_SDKS_ROOT'):
        #     raise RuntimeError('You seem to be using AutoSDK, which is not supported yet')
        gdk = os.getenv('GameDK')
        if gdk:
            return gdk
        return 'C:\\Program Files (x86)\\Microsoft GDK'

    GDK = find_gdk()
