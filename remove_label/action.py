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
import sys


sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))


from github_api import send_github_json


def update_pr():

    event_json_path = os.environ.get('GITHUB_EVENT_PATH', None)
    if not event_json_path:
        print("Did not find GITHUB_EVENT_PATH environment value.")
        return -1

    event_json_path = pathlib.Path(event_json_path)
    if not event_json_path.exists():
        print(f"Path {event_json_path} was not found.")
        return -2

    with open(event_json_path) as f:
        event_json = json.load(f)

    # /repos/{owner}/{repo}/issues/{issue_number}/labels/{name}
    api_url = f"https://api.github.com/repos/{event_json['repository']['full_name']}/issues/{event_json['pull_request']['number']}/labels/{event_json['label']['name']}"
    print()
    r = send_github_json(api_url, "DELETE")
    if isinstance(r, dict):
        print(f"Failed to removed {event_json['label']['name']}.")
        pprint.pprint(r)
        return -1
    else:
        print(f"Removed {event_json['label']['name']}.")
    return 0


if __name__ == "__main__":
    sys.exit(update_pr())
