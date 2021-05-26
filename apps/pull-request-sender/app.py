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
import requests
import urllib

import flask

import db
import utils

import github_api as gapi
from github_api import env as genv

app = flask.Flask(__name__)


BASE_URL = "pr.gha.openroad.tools"

PROJECT_ID = os.environ['PROJECT_ID']

CLIENT_ID = os.environ['CLIENT_ID']
CLIENT_SECRET = os.environ['CLIENT_SECRET']

# ----------------------------

@app.route("/send", methods=['GET', 'POST'])
def send():
    data = json.loads(flask.request.get_data())
    event_json = data['event_json']
    private, staging, upstream, pr_sha = genv.details_from_json(data['env'])

    assert private.sender is not None, (private, staging, upstream)

    # Refresh the auth token
    t = db.Token.latest(private.sender)
    with db.client.context():
        t = refresh_token(t)
        if not isinstance(t, db.Token):
            return t+'\n'
    assert t.access_token is not None, t

    pr_api_url = f'https://api.github.com/repos/{staging.slug}/commits/{pr_sha}/pulls'
    prs_json = gapi.get_github_json(
        pr_api_url,
        preview="groot-preview",
        access_token=t.access_token,
    )

    # Only include open pull requests
    prs_json = list(filter(lambda pr: pr['state'] == 'open', prs_json))

    if not prs_json:
        # Need to create a new pull request.
        pr_api_url = f'https://api.github.com/repos/{upstream.slug}/pulls'

        create_pr_json = {
            "base": upstream.branch,
            "head": f"{staging.owner}:{staging.branch}",
            "title": event_json["pull_request"]["title"],
            "body": event_json["pull_request"]["body"],
            "maintainer_can_modify": True,
            "draft": True,
        }
        r = gapi.send_github_json(
            pr_api_url,
            "POST",
            create_pr_json,
            access_token=t.access_token,
        )
        prs_json.append(r)

    if 'number' not in prs_json[-1]:
        return json.dumps(prs_json)+'\n'
    return json.dumps(prs_json[-1])+'\n'


@app.route("/revoke", methods=['GET', 'POST'])
def revoke():
    user = flask.request.args.get('user')
    db.Token.delete(user)
    return f'Removed tokens for {user}'


@app.route("/auth")
def auth():
    info = utils.PRInfo.from_request(flask.request)

    # Redirect user to GitHub login
    rjson = {
        'client_id': CLIENT_ID,
        'redirect_uri': f'https://{BASE_URL}/token',
        'state': info.to_token(),
        'login': info.user,
        'allow_signup': False,
    }

    d = requests.get(
        url="https://github.com/login/oauth/authorize",
        json=rjson,
        allow_redirects=False,
    )
    return flask.redirect(d.headers['Location'])


@app.route("/token", methods=['GET'])
def token():
    info = utils.PRInfo.from_request(flask.request)

    code = flask.request.args.get('code')

    d = requests.get(
        url="https://github.com/login/oauth/access_token",
        json = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'code': code,
        },
        allow_redirects=False,
    )

    with db.client.context():
        t = db.Token.from_response(info.user, d)
        if not isinstance(t, db.Token):
            return t

        t.put()

    # Ask the check to refresh
    return flask.redirect(info.hook_url)


def refresh_token(t):
    d = requests.get(
        url="https://github.com/login/oauth/access_token",
        json = {
            'refresh_token': t.refresh_token,
            'grant_type': 'refresh_token',
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
        },
        allow_redirects=False,
    )

    t = db.Token.from_response(t.login, d)
    if not isinstance(t, db.Token):
        return t

    t.put()
    return t


@app.route("/refresh")
def refresh():
    user = flask.request.args.get('user')

    # Get existing token
    t = db.Token.latest(user)
    before = t.to_table()

    # Refresh the token
    with db.client.context():
        t = refresh_token(t)
        after = t.to_table()

    return f"""\
<html>
 <body>
  <h1>Before Refresh</h1>
{before}

  <br>

   <h1>After Refresh</h1>
{after}

 </body>
</html>
"""


@app.route("/")
def index():
    info = utils.PRInfo.from_request(flask.request)

    t = db.Token.latest(info.user)
    return t.to_html()


@app.route("/hook", methods=['GET', 'POST'])
def hook():
    data = json.loads(flask.request.get_data())
    return json.dumps(data, sort_keys=True, indent=2)

# ----------------------------

# Redirect {BASE_URL}/localhost/<url> to enable OAuth authentication when
# developing locally via redirected through the production URL.
@app.route("/localhost/<rurl>")
def localhost(rurl):
    qs = flask.request.query_string.decode('utf-8')
    lurl = f"http://localhost:8080/{rurl}?{qs}"
    return flask.redirect(lurl)
