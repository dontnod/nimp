

        # Visual Studio maybe?
        for file in os.listdir('.'):
            if os.path.splitext(file)[1] == '.sln' and os.path.isfile(file):
                platform, config = 'Any CPU', 'Release'
                if hasattr(env, 'platform') and env.platform is not None:
                    platform = env.platform
                if hasattr(env, 'configuration') and env.configuration is not None:
                    config = env.configuration

                sln = open(file).read()
                vsver = '11'
                if '# Visual Studio 2012' in sln:
                    vsver = '11'
                elif '# Visual Studio 2013' in sln:
                    vsver = '12'

                return nimp.build.vsbuild(file, platform, config, env.target, vsver, 'Build')

        logging.error("Invalid project type %s", env.project_type)
        return False

