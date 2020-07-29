
import nimp.sys.platform

class Win32(nimp.sys.platform.Platform):
    ''' Win32 platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'win32'
        self.aliases = set(['pcconsole'])


class Win64(nimp.sys.platform.Platform):
    ''' Win64 platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'win64'
        self.aliases = set(['pc', 'windows'])


class Linux(nimp.sys.platform.Platform):
    ''' Linux platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'linux'


class Mac(nimp.sys.platform.Platform):
    ''' Mac platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'mac'
        self.aliases = set(['macos', 'osx'])
