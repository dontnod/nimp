
import os
import nimp.sys.platform

class XboxOne(nimp.sys.platform.Platform):
    ''' XboxOne platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'xboxone'
        self.is_microsoft = True

        self.layout_file_extension = 'xml'
        self.package_tool_path = os.path.join(os.environ['DurangoXDK'], 'bin', 'MakePkg.exe')

        self.ue4_name = 'XboxOne'
