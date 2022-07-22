#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021 OpenROAD Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import json
import os
import pprint
import threading
import traceback
import time

import flask

import github_api as gapi

app = flask.Flask(__name__)


BASE_URL = "up.gha.openroad.tools"

PROJECT_ID = os.environ['PROJECT_ID']

CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']

# ----------------------------

WORKFLOW_ID = 'github-actions-cron-sync-fork-from-upstream.yml'
HEAD_REF = 'refs/heads/'


class DispatchTargets:
    _cache = None
    _cache_updated = 0
    _cache_lock = threading.Lock()

    @classmethod
    def get(cls):
        now = time.time()

        targets = cls._cache
        if now - cls._cache_updated > 60*5:
            if not cls._cache_lock.acquire(blocking=False):
                # Is another thread is updating the cache, first try and
                # return the old values, otherwise wait for them to be
                # populated.
                while True:
                    targets = cls._cache
                    if targets:
                        return targets
                    time.sleep(0.1)

            try:
                installs = gapi.get_github_json(
                    'https://api.github.com/app/installations', jwt=True)

                targets = []
                for i in installs:
                    targets.append(i["account"]["login"])
                targets = tuple(targets)

                cls._cache = targets
                cls._cache_updated = now

            finally:
                cls._cache_lock.release()

        return targets


def trigger_workflow_dispatch(owner, repo, branch):
    # https://docs.github.com/en/rest/reference/actions#create-a-workflow-dispatch-event
    # /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches
    # workflow_id: The ID of the workflow. You can also pass the workflow file name as a string.
    url = f'https://api.github.com/repos/{owner}/{repo}/actions/workflows/{WORKFLOW_ID}/dispatches'
    # Payload:
    #  ref: The git reference for the workflow. The reference can be a branch or tag name.
    #  inputs: Input keys and values configured in the workflow file.
    payload = {'ref': branch}
    return gapi.send_github_json(url, 'POST', payload, slug=f'{owner}/{repo}')


def trigger_workflow_dispatches(repo, branch):
    results = {}
    for owner in DispatchTargets.get():
        try:
            results[owner] = trigger_workflow_dispatch(owner, repo, branch)
        except Exception as e:
            results[owner] = {
                'message': str(e),
                'owner': owner,
                'repo': repo,
                'breanch': branch,
                'traceback': traceback.format_exc(),
            }
    return results


@app.route("/hook", methods=['GET', 'POST'])
def hook():
    data = json.loads(flask.request.get_data())
    try:
        repo = data['repository']['name']
        head = data['ref']
        assert head.startswith(HEAD_REF), (head, HEAD_REF)
        branch = head[len(HEAD_REF):]

        results = []
        if branch in ('master', 'main'):
            results = trigger_workflow_dispatches(repo, branch)

        return json.dumps(results, sort_keys=True, indent=2)

    except Exception as e:
        return str(e)+'\n'+json.dumps(data, sort_keys=True, indent=2)


@app.route("/manual", methods=['GET', 'POST'])
def manual():
    repo = flask.request.args.get('repo')
    if not repo:
        return 'Missing required "repo" argument.'
    branch = flask.request.args.get('branch')
    if not branch:
        return 'Missing required "branch" argument.'

    results = trigger_workflow_dispatches(repo, branch)
    return json.dumps(results, sort_keys=True, indent=2)


@app.route("/")
def installs():
    return json.dumps(DispatchTargets.get())
