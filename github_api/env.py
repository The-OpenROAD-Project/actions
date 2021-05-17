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
import json
import os
import pathlib
import pprint

from typing import Optional

from . import get_github_json


@dataclasses.dataclass
class Repo:
    owner: str
    repo: str
    branch: str
    pr: Optional[int] = None

    @property
    def slug(self):
        return f"{self.owner}/{self.repo}"

    @property
    def branch_url(self):
        return f"https://github.com/{self.slug}/tree/{self.branch}"

    @property
    def pr_url(self):
        assert self.pr is not None, self
        return f"https://github.com/{self.slug}/pull/{self.pr}"


def get_event_json():
    event_json_path = os.environ.get('GITHUB_EVENT_PATH', None)
    if not event_json_path:
        raise SystemError("Did not find GITHUB_EVENT_PATH environment value.")

    event_json_path = pathlib.Path(event_json_path)
    if not event_json_path.exists():
        raise SystemError(f"Path {event_json_path} was not found.")

    with open(event_json_path) as f:
        event_json = json.load(f)

    print()
    print("::group::Event JSON raw")
    print(open(event_json_path).read())
    print("::endgroup::")
    print()
    print("::group::Event JSON details")
    pprint.pprint(event_json)
    print("::endgroup::")
    print()
    return event_json


def details(event_json):
    # As there are three repositories involved here, things can get a bit
    # confusing.
    #
    #  * 'event_json` is associated with the **private** repository that the
    #    branch originated from.
    #
    #  * `staging_.*` is the **public** staging repository we are going to be
    #    sending the pull request **from**. The branch specified in
    #    `event_json` was replicated from the **private** repository too the
    #    staging repository.
    #
    #  * `upstream_.*` is the **public** repository we are going to be sending
    #    the pull request **to**.
    private = Repo(
        owner = os.environ.get(
            'PRIVATE_OWNER',
            event_json['pull_request']['head']['repo']['owner']['login']),
        repo = os.environ.get(
            'PRIVATE_REPO',
            event_json['pull_request']['head']['repo']['name']),
        branch = os.environ.get(
            'PRIVATE_BRANCH',
            event_json['pull_request']['head']['ref']),
        pr = event_json["pull_request"]["number"])

    repo_json = get_github_json(f'https://api.github.com/repos/{private.slug}')
    repo_default_name = repo_json['parent']['name']

    staging = Repo(
        owner = os.environ.get(
            'STAGING_OWNER',
            'The-OpenROAD-Project-staging'),
        repo = os.environ.get(
            'STAGING_REPO',
            repo_default_name),
        branch = os.environ.get(
            'STAGING_BRANCH',
            event_json['pull_request']['head']['ref']),
    )

    upstream = Repo(
        owner = os.environ.get(
            'UPSTREAM_OWNER',
            'The-OpenROAD-Project'),
        repo = os.environ.get(
            'UPSTREAM_REPO',
            repo_default_name),
        branch = os.environ.get(
            'UPSTREAM_BRANCH',
            'master'),
        pr = os.environ.get(
            'UPSTREAM_PR',
            None),
    )

    print()
    print(" Private:", private.slug,  "@", private.branch,  "(", private.branch_url,  ")")
    print(" Staging:", staging.slug,  "@", staging.branch,  "(", staging.branch_url,  ")")
    print("Upstream:", upstream.slug, "@", upstream.branch, "(", upstream.branch_url, ")")
    print()
    pr_sha = event_json['pull_request']['head']['sha']
    pr_sha_url = f"https://github.com/{private.slug}/commits/{pr_sha}"
    print()
    print(" Pull request @", pr_sha, "(", pr_sha_url, ")")
    print()

    return (private, staging, upstream, pr_sha)
