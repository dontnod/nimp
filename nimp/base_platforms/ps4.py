
import nimp.sys.platform

class PS4(nimp.sys.platform.Platform):
    ''' PS4 platform description '''

    def __init__(self):
        super().__init__()

        self.name = 'ps4'
        self.aliases = set(['orbis'])

        self.layout_file_extension = 'gp4'
