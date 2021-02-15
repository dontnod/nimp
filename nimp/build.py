# -*- coding: utf-8 -*-
# Copyright (c) 2014-2019 Dontnod Entertainment

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

''' Utilities related to compilation '''

import logging
import os
import glob
import socket
import subprocess
import re

import nimp.system
import nimp.sys.platform
import nimp.sys.process

def msbuild(project_file, platform_name, configuration, project=None,
            vs_version='14', dotnet_version='4.6', additional_flags=None ):
    ''' Builds a project with MSBuild '''

    # Windows
    if nimp.sys.platform.is_windows():
        msbuild_path = _find_msbuild_path(vs_version)
        if msbuild_path is None:
            return False

        needCapture = True

    # Mac and Linux alike
    else:
        msbuild_path = 'xbuild'
        needCapture = False

    command = [ msbuild_path, project_file,
                '/verbosity:minimal',
                '/nologo',
                '/p:TargetFrameworkVersion=v' + dotnet_version,
                '/p:TargetFrameworkProfile=' ]

    if project is not None:
        command.append('/target:' + project)
    if platform_name is not None:
        platform_name = '"' + platform_name + '"' if ' ' in platform_name else platform_name
        command.append('/p:Platform=' + platform_name)
    if configuration is not None:
        configuration = '"' + configuration + '"' if ' ' in configuration else configuration
        command.append('/p:Configuration=' + configuration)
    if additional_flags is not None:
        command += additional_flags

    result, output, _ = nimp.sys.process.call(command, capture_output=needCapture)

    if nimp.sys.platform.is_windows() and 'Cannot run if when setup is in progress.' in output:
        logging.error('Visual Studio appears to have failed')
        return False

    return result == 0

def vsbuild(solution, platform_name, configuration, project=None,
            vs_version='14', target='Build', dotnet_version='4.6', use_msbuild=False):
    ''' Builds a project with Visual Studio '''

    # Windows
    if nimp.sys.platform.is_windows():
        if use_msbuild:
            msbuild_path = _find_msbuild_path(vs_version)
            if msbuild_path is None:
                logging.error('Unable to find Visual Studio %s', vs_version)
                return False
            command = [ msbuild_path, solution, '/verbosity:minimal', '/nologo',
                       '/p:Configuration=' + configuration,
                       '/p:Platform=' + platform_name,
                       '/p:TargetFrameworkVersion=v' + dotnet_version,
                       '/p:TargetFrameworkProfile=']
            if project is not None:
                command = command + ['/target:' + project]

        else:
            devenv_path = _find_devenv_path(vs_version)
            if devenv_path is None:
                logging.error('Unable to find Visual Studio %s', vs_version)
                return False
            command = [ devenv_path, solution ]
            command = command + [ '/' + target, configuration + '|' + platform_name ]
            if project is not None:
                command = command + [ '/project', project ]

        result, output, _ = nimp.sys.process.call(command, capture_output=True)
        if 'Cannot run if when setup is in progress.' in output:
            logging.error('Visual Studio appears to have failed')
            return False

        return result == 0

    # Mac and Linux alike
    command = [ 'xbuild', solution, '/verbosity:quiet', '/nologo',
                '/p:Configuration=' + configuration,
                '/p:Platform=' + platform_name,
                '/p:TargetFrameworkVersion=v' + dotnet_version,
                '/p:TargetFrameworkProfile=' ]
    if project is not None:
        command = command + [ '/target:' + project ]
    return nimp.sys.process.call(command) == 0

def _find_msbuild_path(vs_version):
    msbuild_path = None

    # Sanitize vs_version
    if vs_version == '2015':
        vs_version = '14.0'
    if vs_version == '2017':
        vs_version = '15.0'
    if vs_version == '2019':
        # Changed path : MSBuild is installed in the \Current folder
        # https://docs.microsoft.com/en-us/visualstudio/msbuild/whats-new-msbuild-16-0?view=vs-2019
        vs_version = 'Current'

    # For VS2017 and later, there is vswhere
    vswhere_cmd = [ os.path.join(os.environ['ProgramFiles(x86)'], 'Microsoft Visual Studio/Installer/vswhere.exe') ]
    vswhere_cmd += [ '-products', '*', '-requires', 'Microsoft.Component.MSBuild', '-property', 'installationPath' ]
    result, output, _ = nimp.sys.process.call(vswhere_cmd, capture_output=True, hide_output=True)
    if result == 0:
        for line in output.split('\n'):
            line = line.strip()
            msbuild_path = os.path.join(line, 'MSBuild', vs_version, 'Bin', 'MSBuild.exe')
            if os.path.exists(msbuild_path):
                break

    if not os.path.exists(msbuild_path):
        logging.error('Unable to find MSBuild %s (%s)', vs_version, msbuild_path)
        return None

    msbuild_path = os.path.normpath(msbuild_path)
    return msbuild_path


def _find_devenv_path(vs_version):
    devenv_path = None

    # Sanitize vs_version
    if vs_version == '2015':
        vs_version = '14'
    if vs_version == '2017':
        vs_version = '15'
    if vs_version == '2019':
        vs_version = '16'

    # First try the registry, because the environment variable is unreliable
    # (case of Visual Studio installed on a different drive; it still sets
    # the envvar to point to C:\Program Files even if devenv.com is on D:\)
    #pylint: disable=import-error
    from winreg import OpenKey, QueryValue, HKEY_LOCAL_MACHINE
    key_path = 'SOFTWARE\\Classes\\VisualStudio.accessor.' + vs_version + '.0\\shell\\Open'
    try:
        with OpenKey(HKEY_LOCAL_MACHINE, key_path) as key:
            cmdline = QueryValue(key, 'Command')
            if cmdline[:1] == '"':
                cmdline = cmdline.split('"')[1]
            elif ' ' in cmdline:
                cmdline = cmdline.split(' ')[0]
            devenv_path = cmdline.replace('devenv.exe', 'devenv.com')
    #pylint: disable=broad-except
    except Exception:
        pass

    # For VS2017 and later, there is vswhere
    if not devenv_path:
        vswhere_path = os.path.join(os.environ['ProgramFiles(x86)'], 'Microsoft Visual Studio/Installer/vswhere.exe')
        result, output, _ = nimp.sys.process.call([vswhere_path], capture_output=True, hide_output=True)
        if result == 0:
            for line in output.split('\n'):
                line = line.strip()
                if 'installationPath: ' in line:
                    candidate = line.split(' ', 1)[1]
                elif 'installationVersion: ' + vs_version in line:
                    devenv_path = os.path.join(candidate, 'Common7/IDE/devenv.com')
                    break

    # If the registry key is unhelpful, try the environment variable
    if not devenv_path:
        vstools_path = os.getenv('VS' + vs_version + '0COMNTOOLS')
        if vstools_path is not None:
            # Sanitize this because os.path.join sometimes gets confused
            if vstools_path[-1] in [ '/', '\\' ]:
                vstools_path = vstools_path[:-1]
            devenv_path = os.path.join(vstools_path, '../../Common7/IDE/devenv.com')

    if not devenv_path or not os.path.exists(devenv_path):
        return None

    devenv_path = os.path.normpath(devenv_path)
    logging.info("Found Visual Studio at %s", devenv_path)
    return devenv_path

def install_distcc_and_ccache():
    """ Install environment variables suitable for distcc and ccache usage
        if relevant.
    """
    distcc_dir = '/usr/lib/distcc'
    ccache_dir = '/usr/lib/ccache'

    # Make sure distcc will be called if we use ccache
    if os.path.exists(distcc_dir):
        logging.info('Found distcc, so setting CCACHE_PREFIX=distcc')
        os.environ['CCACHE_PREFIX'] = 'distcc'

    # Add ccache to PATH if it exists, otherwise add distcc
    if os.path.exists(ccache_dir):
        extra_path = ccache_dir
    elif os.path.exists(distcc_dir):
        extra_path = distcc_dir
    else:
        return
    logging.info('Adding %s to PATH', extra_path)
    os.environ['PATH'] = extra_path + ':' + os.getenv('PATH')

    if os.path.exists(distcc_dir):
        # Set DISTCC_HOSTS if necessary
        if not os.getenv('DISTCC_HOSTS'):
            hosts = subprocess.Popen(['lsdistcc'], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
            hosts = ' '.join(hosts.split())
            logging.debug('Setting DISTCC_HOSTS=%s', hosts)
            os.environ['DISTCC_HOSTS'] = hosts

        # Compute a reasonable number of workers for UBT
        if not os.getenv('UBT_PARALLEL'):
            workers = subprocess.Popen(['distcc', '-j'], stdout=subprocess.PIPE).communicate()[0].decode('utf-8')
            logging.debug('Setting UBT_PARALLEL=%s', workers)
            os.environ['UBT_PARALLEL'] = workers

def upload_symbols(env, symbols, config):
    ''' Uploads build symbols to a symbol server '''
    if not (env.is_win64 or env.is_xsx or env.is_ps5):
        logging.error("Plafrom must be win64, xsx or ps5")
        return False

    def _discover_latest_autosdk(platform):
        '''look for autoSDK on buildmachine '''
        # TODO: get this out of here and in a more generic place like system for example
        host_name = socket.gethostname()
        is_build_worker = host_name.startswith('farmagent') or host_name.startswith('linuxagent')
        platform = 'GDK' if platform in ['win64', 'xsx'] else platform
        auto_sdk_root = 'D:/autoSDK/HostWin64/' + platform.upper()
        if not is_build_worker or not os.path.exists((auto_sdk_root)):
            return None

        possible_paths = os.listdir(auto_sdk_root)
        if platform == 'ps5':
            # possible falvours : PS5/2.00.00.09/NotForLicensees/2.000/
            # possible falvours : PS5/2.000.009/NotForLicensees/2.000/
            pattern = r'^\d?(\d).\d+.\d+?(.\d+)$'

        else:
            # possible flavours like GDK/200806/
            pattern = r'^\d{6}$'
        possible_paths = sorted([ p for p in possible_paths if re.match(pattern, p)], reverse=True )
        if platform == 'ps5': # sort possible flavours like 2.00.00.89 and 2.000.089, sigh...
            dotless_paths = sorted([ (path.replace('.', ''), path) for path in possible_paths ], reverse=True)
            possible_paths = [ dot for dotless, dot in dotless_paths ]
            if possible_paths != []: # second round of version guessing for ps5, sigh...
                auto_sdk_root += '/' + possible_paths[0] + '/NotForLicensees/'
                possible_paths = os.listdir(auto_sdk_root)
                possible_paths = sorted([p for p in possible_paths if re.match(r'\d?(\d).\d+', p)], reverse=True)
        if possible_paths == []:
            return None
        auto_sdk_root += '/' + possible_paths[0]
        return auto_sdk_root

    # create store if not available yet
    store_root = nimp.system.sanitize_path(os.path.join(env.format(env.publish_symbols), env.platform.lower()))
    if not os.path.exists(store_root):
        nimp.system.safe_makedirs(store_root)

    # find the tool to upload our symbols
    sym_tool_path = "C:/Program Files (x86)/Windows Kits/10/Debuggers/x64/symstore.exe"
    if env.is_ps5: # ps5 sym tool
        auto_sdk_root = _discover_latest_autosdk(env.platform)
        prospero_local_root = os.getenv('SCE_PROSPERO_SDK_DIR', default=None)
        assert prospero_local_root or auto_sdk_root
        ps5_sdk_root = auto_sdk_root if auto_sdk_root else prospero_local_root
        sym_tool_path = os.path.join(ps5_sdk_root, 'host_tools', 'bin', 'prospero-symupload.exe')
    else: # autoSDK win10 sdk
        win10_sdk_path = 'D:/autoSDK/HostWin64/Win64/Windows Kits/10/Debuggers/x64/symstore.exe'
        if os.path.isfile(win10_sdk_path):
            sym_tool_path = win10_sdk_path
    sym_tool_path = nimp.system.sanitize_path(sym_tool_path)
    logging.debug('Using sym-too-path -> %s' % sym_tool_path)

    # Create response file
    index_file = "symbols_index.txt"
    with open(index_file, "w") as symbols_index:
        for src, _ in symbols:
            symbols_index.write(src + "\n")
    # transaction tag
    transaction_comment = "{0}_{1}_{2}_{3}".format(env.project, env.platform, config, env.revision)

    # common cmd params
    compress = "/compress" if hasattr(env, 'compress') and env.compress else ""
    cmd = [
        sym_tool_path,
        "add",
        "/r", # Recursive
        "/f", "@" + index_file, # add files from response file
        "/s", store_root, # target symbol store
        "/o", # Verbose output
        compress, # compression
    ]
    # platform specific cmd params
    if env.is_ps5:
        cmd += [
            "/tag", transaction_comment, # tag symbols
        ]
    if env.is_microsoft_platform:
        cmd += [
            "/t", env.project, # Product name
            "/c", transaction_comment,
            "/v", env.revision,
        ]

    if nimp.sys.process.call(cmd) != 0:
        # Do not remove symbol index; keep it for later debugging
        return False

    os.remove(index_file)

    return True

def get_symbol_transactions(symsrv):
    ''' Retrieves all symbol transactions from a symbol server '''
    server_txt_path =  os.path.join(symsrv, "000Admin", "server.txt")
    if not os.path.exists(server_txt_path):
        logging.error("Unable to find the file %s, aborting.", server_txt_path)
        return None
    line_re = re.compile(r"^(?P<id>\d*),"
                         r"(?P<operation>(add|del)),"
                         r"(?P<type>(file|ptr)),"
                         r"(?P<creation_date>\d{2}\/\d{2}\/\d{4}),"
                         r"(?P<creation_time>\d{2}:\d{2}:\d{2}),"
                         r"\"(?P<product_name>[^\"]*)\","
                         r"\"(?P<version>[^\"]*)\","
                         r"\"(?P<comment>[^\"]*)\",$")
    transaction_infos = []
    with open(server_txt_path, "r") as server_txt:
        for line in server_txt.readlines():
            match = line_re.match(line)
            if not match:
                logging.error("%s is not recognized as a server.txt transaction entry", line)
                return None
            transaction_infos += [match.groupdict()]
    return transaction_infos

def delete_symbol_transaction(symsrv, transaction_id):
    ''' Deletes a symbol transaction from a Microsoft symbol repository '''
    command  = [ "C:/Program Files (x86)/Windows Kits/8.1/Debuggers/x64/symstore.exe",
                 "del",
                 "/i",
                 transaction_id,
                 "/s",
                 symsrv]
    if nimp.sys.process.call(command) != 0:
        return False
    return True
