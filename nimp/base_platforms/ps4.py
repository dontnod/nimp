
import nimp.sys.platform

class PS4(nimp.sys.platform.Platform):
    ''' PS4 platform description '''

    def register(self, env):
        env.ue4_platform_aliases['ps4'] = 'ps4'
        env.ue4_platform_aliases['orbis'] = 'ps4'
