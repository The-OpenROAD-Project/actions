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
import pathlib
import pprint
import requests

from datetime import datetime, timedelta, timezone

import jwt


if 'CLIENT_KEY' in os.environ:
    GH_APP_PRIVATE_KEY = pathlib.Path(os.environ['CLIENT_KEY']).resolve()
    assert GH_APP_PRIVATE_KEY.exists(), GH_APP_PRIVATE_KEY
else:
    GH_APP_PRIVATE_KEY = pathlib.Path(__file__).parent / pathlib.Path("app.private-key.pem")


def get_bearer_token():
    if not GH_APP_PRIVATE_KEY.exists():
        raise SystemError(f'Needed a bearer token but missing {GH_APP_PRIVATE_KEY}')
        return None

    app_id = int(os.environ.get('APP_ID', os.environ.get('GITHUB_APP_ID', 0)))
    assert app_id != 0

    with open(GH_APP_PRIVATE_KEY, 'rb') as fh:
        private_key = jwt.jwk_from_pem(fh.read())

    i = jwt.JWT()

    # Generate the JWT
    payload = {
      # issued at time, 60 seconds in the past to allow for clock drift
      'iat': jwt.utils.get_int_from_datetime(
          datetime.now(timezone.utc) - timedelta(seconds=60)),
      # JWT expiration time (10 minute maximum)
      'exp': jwt.utils.get_int_from_datetime(
        datetime.now(timezone.utc) + timedelta(minutes=10)),
      # GitHub App's identifier
      'iss': app_id,
    }

    return i.encode(payload, private_key, alg="RS256")


def get_github_json_jwt(url, method='GET'):
    btoken = get_bearer_token()
    assert btoken is not None, (url, method)
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": "Bearer "+btoken,
    }
    f = getattr(requests, method.lower())
    return f(url=url, headers=headers).json()


def get_token(slug=os.environ.get('GITHUB_REPOSITORY', None)):
    assert slug is not None
    install_data = get_github_json_jwt(
        f"https://api.github.com/repos/{slug}/installation")

    assert 'id' in install_data, pprint.pformat(install_data)
    install_id = install_data['id']

    access_data = get_github_json_jwt(
        install_data['access_tokens_url'], method='POST')
    return access_data['token']


if __name__ == "__main__":
    print(get_token())
