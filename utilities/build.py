# -*- coding: utf-8 -*-

from utilities.processes import *

#---------------------------------------------------------------------------
def vsbuild(solution, platform, configuration, project = None, vs_version = '12', target = 'build'):
    build_directory = '.'

    devenv_path = _find_devenv_path(vs_version)
    if devenv_path is None:
        log_error('Unable to find Visual Studio {0}', vs_version)
        return False

    command = [devenv_path, solution]
    if project is not None:
        command = command + [ '/project', project ]
    command = command + [ '/' + target, configuration + '|' + platform ]
    return call_process(build_directory, command)

#-------------------------------------------------------------------------------
def _find_devenv_path(vs_version):
    devenv_path     = None
    vstools_path    = os.getenv('VS' + vs_version + '0COMNTOOLS')
    if vstools_path is not None:
        devenv_path = os.path.join(vstools_path, '../../Common7/IDE/devenv.com')
        if os.path.exists(devenv_path):
            log_verbose('Found Visual Studio at {0}', devenv_path)
    return devenv_path
