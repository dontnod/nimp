
import nimp.sys.platform

class IOS(nimp.sys.platform.Platform):
    ''' IOS platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'ios'