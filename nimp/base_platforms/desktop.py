
import nimp.sys.platform

class Desktop(nimp.sys.platform.Platform):
    ''' Desktop platform description '''

    def register(self, env):
        env.ue4_platform_aliases['win32'] = 'win32'
        env.ue4_platform_aliases['pcconsole'] = 'win32'

        env.ue4_platform_aliases['win64'] = 'win64'
        env.ue4_platform_aliases['pc'] = 'win64'
        env.ue4_platform_aliases['windows'] = 'win64'

        env.ue4_platform_aliases['linux'] = 'linux'

        env.ue4_platform_aliases['mac'] = 'mac'
        env.ue4_platform_aliases['macos'] = 'mac'
