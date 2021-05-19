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


import dataclasses
import enum
import json
import os
import requests


from datetime import datetime


def fromisoformat(s):
    """

    >>> fromisoformat('2021-05-03T01:48:37Z')
    datetime.datetime(2021, 5, 3, 1, 48, 37, tzinfo=datetime.timezone.utc)

    >>> repr(fromisoformat(None))
    'None'
    """
    if not s or s == 'null':
        return None
    if s.endswith('Z'):
        s = s[:-1]+'+00:00'
    return datetime.fromisoformat(s)


def toisoformat(s):
    """

    >>> toisoformat(datetime(2021, 5, 3, 1, 48, 37, tzinfo=timezone.utc))
    '2021-05-03T01:48:37Z'
    >>> toisoformat(datetime(2021, 5, 3, 1, 48, 37, tzinfo=None))
    '2021-05-03T01:48:37Z'
    """
    if s is None:
        return None
    else:
        assert s.tzinfo in (timezone.utc, None), (s.tzinfo, repr(s), str(s))
        if s.tzinfo == timezone.utc:
            return datetime.isoformat(s).replace('+00:00', 'Z')
        elif s.tzinfo is None:
            return datetime.isoformat(s) + 'Z'


TOKEN_ENV_NAME = 'GITHUB_TOKEN'


def github_headers(preview=None, _headers={}):
    if not _headers:
        # Figure out the GitHub access token.
        access_token = os.environ.get(TOKEN_ENV_NAME, None)
        if not access_token:
            from . import app_token
            access_token = app_token.get_token()
            if not access_token:
                raise SystemError(
                    f'Did not find an access token of `{TOKEN_ENV_NAME}`')
        _headers['Authorization'] = 'token ' + access_token
    if preview is None:
        _headers['Accept'] = 'application/vnd.github.v3+json'
    else:
        _headers['Accept'] = f'application/vnd.github.{preview}+json'
    return _headers


def cleanup_json_dict(d):
    """
    >>> d = {'a': None, 'b': {'c': None, 'd': 1}}
    >>> cleanup_json_dict(d)
    >>> d
    {'b': {'d': 1}}
    """

    for k, v in list(d.items()):
        if isinstance(v, dict):
            cleanup_json_dict(v)
        elif v is None:
            del d[k]
        elif isinstance(v, enum.Enum):
            d[k] = v.value
        elif isinstance(v, datetime):
            d[k] = fromisoformat(v)


def send_github_json(url, mode, json_data=None, preview=None):
    assert mode in ('GET', 'POST', 'PATCH', 'DELETE'), f"Unknown mode {mode}"

    if dataclasses.is_dataclass(json_data):
        json_data = dataclasses.asdict(json_data)
        cleanup_json_dict(json_data)

    kw = {
        'url': url,
        'headers': github_headers(preview=preview),
    }
    if mode == 'POST':
        f = requests.post
        assert json_data is not None, json_data
        kw['json'] = json_data
    elif mode == 'PATCH':
        f = requests.patch
        assert json_data is not None, json_data
        kw['json'] = json_data
    elif mode == 'GET':
        assert json_data is None, json_data
        f = requests.get
    elif mode == 'DELETE':
        assert json_data is None, json_data
        f = requests.delete
        return f(**kw).json()

    json_data = f(**kw).json()
    return json_data


def get_github_json(url, *args, **kw):
    preview = kw.pop('preview', None)
    full_url = url.format(*args, **kw)
    return send_github_json(full_url, 'GET', preview=preview)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
