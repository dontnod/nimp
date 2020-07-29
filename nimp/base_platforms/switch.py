
import nimp.sys.platform

class Switch(nimp.sys.platform.Platform):
    ''' Switch platform description '''

    def register(self, env):
        env.ue4_platform_aliases['switch'] = 'switch'
