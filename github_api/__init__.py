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

import datetime as dt


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
    return dt.datetime.fromisoformat(s)


def toisoformat(s):
    """

    >>> toisoformat(dt.datetime(2021, 5, 3, 1, 48, 37, tzinfo=dt.timezone.utc))
    '2021-05-03T01:48:37Z'
    >>> toisoformat(dt.datetime(2021, 5, 3, 1, 48, 37, tzinfo=None))
    '2021-05-03T01:48:37Z'
    """
    if s is None:
        return None
    else:
        assert s.tzinfo in (dt.timezone.utc, None), (s.tzinfo, repr(s), str(s))
        if s.tzinfo == dt.timezone.utc:
            return dt.datetime.isoformat(s).replace('+00:00', 'Z')
        elif s.tzinfo is None:
            return dt.datetime.isoformat(s) + 'Z'


TOKEN_ENV_NAME = 'GITHUB_TOKEN'


_ACCESS_TOKEN_CACHE = {}


def get_access_token(slug=None):
    if slug not in _ACCESS_TOKEN_CACHE:
        env_token = os.environ.get(TOKEN_ENV_NAME, None)

        if slug is None:
            if env_token is not None:
                return env_token
            else:
                slug = os.environ.get('GITHUB_REPOSITORY')

        assert slug is not None, slug

        from . import app_token
        access_token = app_token.get_token(slug=slug)
        if not access_token:
            raise SystemError(
                f'Did not find an access token of `{TOKEN_ENV_NAME}`')

        _ACCESS_TOKEN_CACHE[slug] = access_token

    assert _ACCESS_TOKEN_CACHE[slug] is not None, (slug, _ACCESS_TOKEN_CACHE)
    return _ACCESS_TOKEN_CACHE[slug]


def github_headers(preview=None, slug=None, access_token=None):
    if access_token is None:
        access_token = get_access_token(slug)

    h = {}
    if access_token:
       h['Authorization'] = 'token ' + access_token
    if preview is None:
       h['Accept'] = 'application/vnd.github.v3+json'
    else:
       h['Accept'] = f'application/vnd.github.{preview}+json'

    return h


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
        elif isinstance(v, dt.datetime):
            d[k] = toisoformat(v)


def send_github_json(url, mode, json_data=None, preview=None, slug=None, access_token=None):
    assert mode in ('GET', 'POST', 'PATCH', 'DELETE'), f"Unknown mode {mode}"

    if dataclasses.is_dataclass(json_data):
        json_data = dataclasses.asdict(json_data)
        cleanup_json_dict(json_data)

    kw = {
        'url': url,
        'headers': github_headers(preview=preview, slug=slug, access_token=access_token),
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

    print(url, mode, json_data, slug)
    r = f(**kw)
    if r.status_code in (204,):
        return (r.status_code, r.reason)
    try:
        json_data = r.json()
        return json_data
    except json.decoder.JSONDecodeError:
        return (r.status_code, r.text)


def get_github_json(url, *args, **kw):
    jwt = kw.pop('jwt', False)
    preview = kw.pop('preview', None)
    slug = kw.get('slug', None)
    access_token = kw.get('access_token', None)

    full_url = url.format(*args, **kw)
    if jwt:
        from . import app_token
        return app_token.get_github_json_jwt(full_url)
    return send_github_json(
        full_url, 'GET',
        preview=preview,
        slug=slug,
        access_token=access_token)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
