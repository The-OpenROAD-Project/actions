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


import datetime
import json
import os
import pprint

import flask

import db
import utils

import github_api as gapi
from github_api import checks


app = flask.Flask(__name__)


BASE_URL = "a.gha.openroad.tools"

PROJECT_ID = os.environ['PROJECT_ID']

CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']

# ----------------------------
NAME = 'PR Sender Authentication'
EXTERNAL_ID = 'pr-auth'


def auth_check_on_private_pr(info):
    assert isinstance(info, utils.PRInfo), info

    if info.slug not in ('mithro/OpenROAD-1',):
        return

    url = f"https://api.github.com/repos/{info.slug}/commits/{info.rev}/check-runs"
    os.environ['GITHUB_REPOSITORY'] = info.slug
    check_runs_json = gapi.get_github_json(url)
    assert 'check_runs' in check_runs_json, pprint.pformat(check_runs_json)

    existing_checks = []
    for c in check_runs_json['check_runs']:
        c.pop('app')
        if c['external_id'] != EXTERNAL_ID:
            continue
        if c['id'] in (2688818725,):
            continue
        existing_checks.append(c)

    t = db.Token.latest(info.user)

    now = datetime.datetime.utcnow()
    if t is None:
        new_check = checks.CheckRunCreate(
            name = NAME,
            head_sha = info.rev,
            external_id = EXTERNAL_ID,

            status = checks.CheckStatus.completed,
            started_at = now,

            conclusion = checks.CheckConclusion.action_required,
            details_url = info.auth_url,
            completed_at = now,

            output = checks.CheckRunCreateOutput(
                title = "Missing credentials for " +info.user,
                summary = f"""\
The pull request sending robot has not be authorized to send pull requests for {info.user}.

[Resolve by having {info.user} click this link.]({info.auth_url})
""",
                text = None,
            ),
            actions = [],
        )
    else:
        # Create the login okay status check.
        new_check = checks.CheckRunCreate(
            name = NAME,
            head_sha = info.rev,
            external_id = EXTERNAL_ID,

            status = checks.CheckStatus.completed,
            started_at = now,

            conclusion = checks.CheckConclusion.success,
            details_url = None,
            completed_at = now,

            output = checks.CheckRunCreateOutput(
                title = "Credentials found for "+info.user,
                summary = f"""\
The pull request sending robot found authorization for {info.user}.

[Double check by having {info.user} click this link.]({info.auth_url})

([Revoke authorization]({info.revoke_url}))
""",
                text = None,
            ),
            actions = [],
        )

    uurl = f"https://api.github.com/repos/{info.slug}/check-runs"
    if not existing_checks:
        r = gapi.send_github_json(uurl, 'POST', new_check)
        return 'Need to *create* this check.'+'\n'+pprint.pformat(r)+'\n'
    else:
        existing_id = existing_checks[0]['id']
        purl = uurl+'/'+str(existing_id)
        r = gapi.send_github_json(purl, 'PATCH', new_check)
        return f'Needed to *update* this check with {existing_id}.'+'\n'+pprint.pformat(r)+'\n'

# ----------------------------

@app.route("/revoke", methods=['GET', 'POST'])
def revoke():
    info = utils.PRInfo.from_request(flask.request)
    db.Token.delete(info.user)
    r = auth_check_on_private_pr(info)
    return flask.redirect(info.pr_url)

# ----------------------------

@app.route("/hook", methods=['GET', 'POST'])
def hook():
    if flask.request.method == 'POST':
        payload = json.loads(flask.request.get_data())
        if 'pull_request' in payload:
            info = utils.PRInfo.from_json(payload['pull_request'])
            r = auth_check_on_private_pr(info)
            if r is not None:
                return r
        return 'Unknown hook action?\n'+json.dumps(payload, sort_keys=True, indent=2)
    else:
        info = utils.PRInfo.from_request(flask.request)
        r = auth_check_on_private_pr(info)
        return flask.redirect(info.pr_url)

# ----------------------------

# Redirect {BASE_URL}/localhost/<url> to enable OAuth authentication when
# developing locally via redirected through the production URL.
@app.route("/localhost/<rurl>")
def localhost(rurl):
    qs = flask.request.query_string.decode('utf-8')
    lurl = f"http://localhost:8080/{rurl}?{qs}"
    return flask.redirect(lurl)


if __name__ == "__main__":
    import sys
    d = json.loads(open(sys.argv[1]).read())
    assert 'pull_request' in d, pprint.pformat(d)
    info = utils.PRInfo.from_json(d['pull_request'])
    print(auth_check_on_private_pr(info))
