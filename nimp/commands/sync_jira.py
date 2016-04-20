# -*- coding: utf-8 -*-

'''Module doc string'''

import argparse
import json
from collections import OrderedDict
import tempfile
from tempfile import mkstemp
import os


from jira import JIRA

from nimp.commands._command import Command
from nimp.utilities.ue4 import ue4_commandlet
from nimp.utilities.logging import log_error
from nimp.utilities.logging import log_notification

#-------------------------------------------------------------------------------
class SynchronizeJiraCommand(Command):
    '''Data mining class. It will retreive all the objects with metadata then create the corresponding jira tasks'''
    def __init__(self):
        '''__init__'''
        Command.__init__(self, 'sync-jira', 'Synchronize Jira')

    def configure_arguments(self, env, parser):
        '''configure_arguments'''
        return True
    #---------------------------------------------------------------------------
    def run(self, env):
        '''
            Method that run the sync-jira nimp command
            Run the DNEAssetMining commandlet that will outpout a json with the ue objects with metadata
            then, it creates the corresponding Jira tasks associated to these objects
        '''
        if env.is_ue4:
            options = { 'server': env.jira_server }
            jira = JIRA(options,basic_auth=(env.jira_id, env.jira_password))

            #Create a new temp file and close it in order that the command let writes in that file
            temp = tempfile.NamedTemporaryFile(delete = False)
            temp.close()
            if ue4_commandlet(env,'DNEAssetMiningCommandlet', 'path=/Game', 'json=%s' % temp.name):
                try:
                    json_file = open(temp.name, encoding='utf-8',errors='replace')
                    json_data = json.loads(json_file.read(), object_pairs_hook=OrderedDict)
                    SynchronizeJiraCommand.parse_json_and_create_jira_task(json_data, jira)
                    json_file.close()
                    os.remove(temp.name)
                except ValueError as error:
                    log_error('ValueError : Invalid characters in Metadata ({0})', temp.name)
        else:
            log_error('This command is only supported on UE4')
        return True

    #---------------------------------------------------------------------------
    @staticmethod
    def parse_json_and_create_jira_task( json_data, jira_object):
        '''Method that parses json_data and then creates the corresponding jira task'''
        for ue_object in json_data:
            summary = ue_object
            description = ''
            for metadata in json_data[ue_object]['Metadata']:
                for key in json_data[ue_object]['Metadata'][metadata]:
                    description += str(json_data[ue_object]['Metadata'][metadata][key]) + ' '
            SynchronizeJiraCommand.create_jira_task(jira_object,'FOR', summary, description, 'Task', None )
        return
    #---------------------------------------------------------------------------
    @staticmethod
    def create_jira_task(jira_object, project, summary, description, issue_type, assignee=None):
        '''Method that creates a jira task with the given paramters, if it already exists, do nothing'''
        #search if issue already exists
        search_str = 'project=\''+project+'\' and summary ~ \'' + summary +'\''
        my_issues = jira_object.search_issues(search_str)
        if len(my_issues) == 0:
            log_notification('Issue ' + summary + ' not found, creating a new one.')
            issue_dict = {
                'project':  { 'key': project },
                'summary': summary,
                'issuetype': { 'name': issue_type },
                'description' : description,
                'assignee': { 'name' : assignee },
            }
            jira_object.create_issue(fields=issue_dict)
        else:
            log_notification('Issue ' + summary + ' already exists.')
        return
