
import nimp.sys.platform

class Android(nimp.sys.platform.Platform):
    ''' Android platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'android'
