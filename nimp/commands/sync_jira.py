# -*- coding: utf-8 -*-
# Copyright (c) 2016 Dontnod Entertainment

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
''' Declares sync-jira command '''

import json
from collections import OrderedDict
import tempfile
import os
import importlib
import logging

import nimp.commands.command
import nimp.ue4
import nimp.p4

#Jira import. That way, if jira module isn't installed for a user, nimp will not crash
_JIRA_IMPORTED = importlib.util.find_spec("jira") is not None
if _JIRA_IMPORTED:
    #pylint: disable=wrong-import-position,wrong-import-order
    from jira import JIRA

class SyncJira(nimp.commands.command.Command):
    '''Retreive all uassets  with metadata then create the corresponding jira tasks'''
    def __init__(self):
        '''__init__'''
        super(SyncJira, self).__init__()

    def configure_arguments(self, env, parser):
        '''configure_arguments'''
        parser.add_argument('--changelists',
                            help    = 'changelists to mine',
                            metavar = 'N',
                            nargs    = '+')
        return True

    def sanitize(self, env):
        return True

    def run(self, env):
        '''
            Method that run the sync-jira nimp command
            Run the DNEAssetMining commandlet that will outpout a json with the ue objects with metadata
            then, it creates the corresponding Jira tasks associated to these objects
        '''
        if _JIRA_IMPORTED :
            if env.is_ue4:
                options = { 'server': env.jira_server }
                jira = JIRA(options,basic_auth=(env.jira_id, env.jira_password))

                #Filter modified files to get only the edited or added ones
                #Only Check in the Content/... p4 folder of the current working directory. It remplaces the condition filename.startswith(os.getcwd()) == true
                packages = nimp.p4.get_modified_files(*env.changelists, root='Content/...')
                filtered_packages = []
                for (filename, action) in packages:
                    if action == 'edit' or action == 'add':
                        if filename.find('Content') != -1 and (filename.find('.uasset') != -1 or filename.find('.umap') != -1):
                            filename = filename.replace('\\','/')
                            filename = filename.split('/Content/')[1]
                            filename = '/Game/' + filename
                            filename = filename.replace('.uasset','')
                            filename = filename.replace('.umap','')
                            filtered_packages.append(filename)

                if len(filtered_packages) == 0:
                    logging.warning('No Packages to mine found in changelists ' + str(env.changelists) +'.')
                    return True

                #Create a new temp file and close it in order that the commandlet writes in that file
                temp = tempfile.NamedTemporaryFile(delete = False)
                temp.close()
                if nimp.ue4.ue4_commandlet(env,'DNEAssetMiningCommandlet', 'packages=%s' % ','.join(filtered_packages), "json=%s" % temp.name):
                    try:
                        json_file = open(temp.name, encoding='utf-8',errors='replace')
                        if os.stat(temp.name).st_size > 0:
                            json_data = json.loads(json_file.read(), object_pairs_hook=OrderedDict)
                            SyncJira.parse_json_and_create_jira_task(env, json_data, jira)
                        else:
                            logging.info('No Metadata found in the mined packages, the file is empty.')
                        json_file.close()
                        os.remove(temp.name)
                    except ValueError:
                        logging.error('ValueError : Invalid characters in Metadata (%s)', temp.name)
            else:
                logging.error('This command is only supported on UE4')
            return True
        else:
            logging.error('Jira Python library is not install. Use "pip3 install jira" to fix this error.')
            return False

    @staticmethod
    def parse_json_and_create_jira_task(env, json_data, jira_object):
        '''Method that parses json_data and then creates the corresponding jira task'''
        if len(json_data) > 0:
            for ue_object in json_data:
                summary = ue_object
                description = ''
                for metadata in json_data[ue_object]['Metadata']:
                    for key in json_data[ue_object]['Metadata'][metadata]:
                        description += key + ' : ' + str(json_data[ue_object]['Metadata'][metadata][key]) + ', '
                SyncJira.create_jira_task(jira_object, env.jira_project_key, summary, description, 'Task', None )
        else:
            logging.info('Json file is not empty but no data was found.')
        return

    @staticmethod
    def create_jira_task(jira_object, project, summary, description, issue_type, assignee=None):
        '''Method that creates a jira task with the given paramters'''
        #search if issue already exists
        search_str = 'project=\''+project+'\' and summary ~ \'' + summary +'\''
        my_issues = jira_object.search_issues(search_str)
        if len(my_issues) == 0:
            logging.info('Issue ' + summary + ' not found, creating a new one.')
            issue_dict = {
                'project':  { 'key': project },
                'summary': summary,
                'issuetype': { 'name': issue_type },
                'description' : description,
                'assignee': { 'name' : assignee },
            }
            jira_object.create_issue(fields=issue_dict)
        else:
            permissions =  jira_object.my_permissions(project, None,  my_issues[0])
            if permissions['permissions']['EDIT_ISSUES']['havePermission']:
                logging.info('Issue ' + summary + ' already exists. Updating description.')
                my_issues[0].update(description = description)
            else:
                logging.warning('Permission Insufficient to edit description on ' + summary + '.')
        return
