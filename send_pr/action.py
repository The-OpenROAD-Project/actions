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
import pathlib
import pprint
import requests
import sys
import urllib


sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))


import github_api
from github_api import get_github_json, send_github_json
from github_api import env as genv


def send_pr():
    event_json = genv.get_event_json()
    private, staging, upstream, pr_sha = genv.details(event_json)
    assert private.sender is not None, (private, staging, upstream)

    data = {
        'event_json': event_json,
        'env': {
            'private': private.as_dict(),
            'staging': staging.as_dict(),
            'upstream': upstream.as_dict(),
            'pr_sha': pr_sha,
        },
    }

    print()
    print("::group::Sending JSON Data")
    print(json.dumps(data))
    print("::endgroup::")
    print()

    pr_json = requests.post(
        url='https://pr.gha.openroad.tools/send',
        json=data,
    ).json()

    print()
    print("::group::Response JSON Data")
    print(json.dumps(pr_json))
    print("::endgroup::")
    print()
    print("::set-output name=pr::"+str(pr_json['number']))

    return


if __name__ == "__main__":
    sys.exit(send_pr())
