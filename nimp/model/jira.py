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


import logging

import requests


logger = logging.getLogger("Jira")


class JiraClient:
    def __init__(self, url, user, password):
        self.service_url = url
        self.service_user = user
        self.service_password = password

    def get_fields(self):
        all_fields = [{"id": "id", "name": "Id", "schema": {"type": "string"}}]
        all_fields += self.api_get("field")

        for field in all_fields:
            if field["id"] == "issuekey":
                field["schema"] = {"type": "string"}

        return all_fields

    def search_issues(self, query, skip=0, limit=None):
        results = []
        results_count = 0
        expected_count = limit

        while (expected_count is None) or (results_count < expected_count):
            parameters = {
                "jql": query,
                "startAt": skip + results_count,
                "maxResults": 100 if limit is None else min(limit - results_count, 100),
            }

            response = self.api_get("search", parameters)
            results_count += len(response["issues"])
            expected_count = response["total"] if limit is None else min(limit, response["total"])
            results += response["issues"]

        return results

    def api_get(self, relative_url, parameters=None):
        parameters = parameters if parameters is not None else {}
        response = requests.get(
            self.service_url + "/rest/api/2/" + relative_url,
            params=parameters,
            auth=(self.service_user, self.service_password),
        )
        response.raise_for_status()
        return response.json()
