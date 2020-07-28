
import nimp.sys.platform

class XboxOne(nimp.sys.platform.Platform):
    ''' XboxOne platform description '''

    def register(self, env):
        env.ue4_platform_aliases['xboxone'] = 'xboxone'
