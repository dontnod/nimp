
import nimp.sys.platform

class XboxOne(nimp.sys.platform.Platform):
    ''' XboxOne platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'xboxone'

        self.layout_file_extension = 'xml'
