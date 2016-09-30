# -*- coding: utf-8 -*-
# Copyright © 2014—2016 Dontnod Entertainment

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
import re
import subprocess

import nimp.system

def vsbuild(solution, platform_name, configuration, project = None, vs_version = '12', target = 'Build'):
    ''' Builds a project with Visual Studio '''
    build_directory = '.'

    if nimp.system.is_windows():
        devenv_path = _find_devenv_path(vs_version)
        if devenv_path is None:
            logging.error("Unable to find Visual Studio %s", vs_version)
            return False
        command = [ devenv_path, solution ]
        command = command + [ '/' + target, configuration + '|' + platform_name ]
        if project is not None:
            command = command + [ '/project', project ]

        return nimp.system.call_process(build_directory, command) == 0

    else: # Mac and Linux alike
        command = [ 'xbuild', solution, '/verbosity:quiet', '/p:TargetFrameworkVersion=v4.5', '/p:TargetFrameworkProfile=', '/nologo' ]
        return nimp.system.call_process(build_directory, command) == 0

def _find_devenv_path(vs_version):
    devenv_path = None

    # First try the registry, because the environment variable is unreliable
    # (case of Visual Studio installed on a different drive; it still sets
    # the envvar to point to C:\Program Files even if devenv.com is on D:\)
    # pylinnt
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

    # If the registry key is unhelpful, try the environment variable
    if not devenv_path:
        vstools_path = os.getenv('VS' + vs_version + '0COMNTOOLS')
        if vstools_path is not None:
            # Sanitize this because os.path.join sometimes gets confused
            if vstools_path[-1] in [ '/', '\\' ]:
                vstools_path = vstools_path[:-1]
            devenv_path = os.path.join(vstools_path, '../../Common7/IDE/devenv.com')

    if not os.path.exists(devenv_path):
        return None

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

def upload_symbols(env, symbols):
    ''' Uploads build symbols to a symbol server '''
    if env.is_microsoft_platform:
        index_file = "symbols_index.txt"
        with open(index_file, "w") as symbols_index:
            for src, _ in symbols:
                symbols_index.write(src + "\n")

        store_root = nimp.system.sanitize_path(env.format(env.publish_symbols))
        transaction_comment = "{0}_{1}_{2}_{3}".format(env.project, env.platform, env.configuration, env.revision)
        cmd = [ "C:/Program Files (x86)/Windows Kits/8.1/Debuggers/x64/symstore.exe",
                "add",
                "/r", # Recursive
                "/f", "@" + index_file,
                "/s", store_root,
                "/o", # Verbose output
                "/t", env.project, # Product name
                "/c", transaction_comment,
                "/v", env.revision, ]
        if hasattr(env, 'compress') and env.compress:
            cmd += [ "/compress" ]

        if nimp.system.call_process(".", cmd) != 0:
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
    if nimp.system.call_process(".", command) != 0:
        return False
    return True

