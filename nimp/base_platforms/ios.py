
import nimp.sys.platform

class IOS(nimp.sys.platform.Platform):
    ''' IOS platform description '''

    def register(self, env):
        env.ue4_platform_aliases['ios'] = 'ios'
