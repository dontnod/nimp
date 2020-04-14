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

''' Validates an UE4 content changelist before it is submitted. '''

import os
import abc
import sys
import shutil
import pathlib
import logging
import nimp.command

def get_client_root(p4):
    ''' Returns current workspace '''
    client_root =  next(p4._parse_command_output(["info"], r"^\.\.\. clientRoot (.*)$"))[0]
    if client_root == '*unknown*':
        return None
    return client_root


def get_dependencies(files):
    command = ['C:/DNE/Git/monorepo/UE4/Engine/Binaries/Win64/DNEAssetRegistryQuery-Win64-Shipping.exe', 'C:/DNE/Git/monorepo/Game/NWD/NWD.uproject', '-AssetFile=stdin', '-OutputFormat=AssetPath', '-DependenciesOnly']
    _, output, error = nimp.sys.process.call(command, stdin='\n'.join(files), capture_output=True)
    return output.splitlines()


class ValidateChangelist(nimp.command.Command):
    ''' Validates an UE4 content changelist before it is submitted. '''
    def __init__(self):
        super(ValidateChangelist, self).__init__()

    def configure_arguments(self, env, parser):
        parser.add_argument('cl_number', help='changelist number', metavar = '<cl_number>')
        nimp.utils.p4.add_arguments(parser)
        return True

    def is_available(self, env):
        return True, ''

    def run(self, env):
        if not nimp.utils.p4.check_for_p4(env):
            return False

        p4 = nimp.utils.p4.get_client(env)

        # Retrieving the depot files in the CL
        depot_files = []
        for depot_file, action in p4._parse_command_output(['describe', env.cl_number],
                                                             r'^\.\.\. depotFile\d* (.*)$',
                                                             r'^\.\.\. action\d* (.*)$'):
            if depot_file is not None:
                depot_files.append(depot_file)

        # Getting the file system path for these files
        files = []
        for depot_file in depot_files:
            for filename in p4._parse_command_output(['where', depot_file], r'^\.\.\. path\d* (.*)$'):
                files.append(filename[0])

        #  Using DNEAssetRegistryQuery to rertrieve the CL files' dependencies
        dependencies = get_dependencies(files)

        # Removing files not in UE4's Content directory as they're almost certainly not in the Perforce depot
        # dependencies not starting by depot + /Game/
        client_rootW = get_client_root(p4)
        client_root = pathlib.PureWindowsPath(client_rootW).as_posix()

        # shortening paths
        deps = []
        deps_in_content = []
        for dep in dependencies:
            s = dep.replace(client_root, '')
            if s.startswith('/Game/'):
                deps_in_content.append(dep)
            deps.append(s)

        # CHECKS
        result = True

        # simple file depot state check
        for dep in deps_in_content:
            if not p4.is_file_versioned(dep):
                logging.error("%s is not versioned.", dep)
                result = False

        statuses = p4.get_files_status(*deps_in_content,)
        for s in statuses:
            if s[2] != None:
                logging.error("%s is modified (or added/deleted) in another changelist.", s[0])
                result = False

        # check for forbidden maps dependencies
        # Looking for .umap
        maps = []
        for f in files:
            if f.endswith('.umap'):
                maps.append(f)

        content_root = client_rootW + '\\Game\\NWD\\Content\\'

        # Si une map est présente dans la changelist (voir NW - Utilisation des dossiers Preprod / Developers):
        # map Preprod ou Gym : ne doit pas référencer d'asset Developers ou des dossiers TME / Vampyr / KiteDemo
        # map officielle : ne doit pas référencer d'asset Developers ou Preprod ou des dossiers TME / Vampyr / KiteDemo

        rules = [[['Preprod\\', 'Gym\\'], ['Developers\\', '\\TME\\', '\\Vampyr\\', '\\KiteDemo\\']],
                 [['Maps\\'], ['Preprod\\', 'Developers\\', '\\TME\\', '\\Vampyr\\', '\\KiteDemo\\']]]

        for m in maps:
            deps = get_dependencies([m])
            m = m.replace(content_root, '')
            for rule in rules:
                start_dirs = rule[0]
                ref_dirs = rule[1]
                for start_dir in start_dirs:
                    if m.startswith(start_dir):
                        for d in deps:
                            for ref_dir in ref_dirs:
                                if ref_dir in d:
                                    logging.error("map %s references %s. Assets from %s should not be referenced by a map from %s subtree.", m, d, ref_dir, start_dir )
                                    result = False

        return result
