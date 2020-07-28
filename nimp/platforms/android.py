
import nimp.sys.platform

class Android(nimp.sys.platform.Platform):
    ''' Android platform description '''

    def register(self, env):
        env.ue4_platform_aliases['android'] = 'android'
