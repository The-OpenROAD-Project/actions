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


import codecs
import dataclasses
import io
import json
import os
import pathlib
import pprint
import sys

from typing import Optional

from . import get_github_json


@dataclasses.dataclass
class Repo:
    owner: str
    repo: str
    branch: str
    pr: Optional[int] = None
    sender: Optional[str] = None

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

    def as_dict(self):
        return dataclasses.asdict(self)


def get_event_json(debug=(os.environ.get('ACTIONS_STEP_DEBUG', None)=='true')):
    event_json_path = os.environ.get('GITHUB_EVENT_PATH', None)
    if not event_json_path:
        raise SystemError("Did not find GITHUB_EVENT_PATH environment value.")

    event_json_path = pathlib.Path(event_json_path)
    if not event_json_path.exists():
        raise SystemError(f"Path {event_json_path} was not found.")

    with open(event_json_path) as f:
        event_json = json.load(f)

    if debug:
        print()
        print("::group::Event JSON raw")
        print(open(event_json_path).read())
        print("::endgroup::")
        print()
        print("::group::Event JSON details")
        pprint.pprint(event_json)
        print("::endgroup::")
        print(flush=True)
    return event_json


def get_repo_default_name(key, private, _cache={}):
    if key in os.environ:
        return os.environ[key]

    if key not in _cache:
        repo_json = get_github_json(f'https://api.github.com/repos/{private.slug}')
        if 'parent' in repo_json:
            _cache[key] = repo_json['parent']['name']
        else:
            _cache[key] = repo_json['name']
    return _cache[key]


def details_from_json(data):
    private  = Repo(**data['private'])
    staging  = Repo(**data['staging'])
    upstream = Repo(**data['upstream'])
    pr_sha   = data['pr_sha']
    return (private, staging, upstream, pr_sha)


def details(event_json=None):
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

    # Support a "rot13 encoded" STAGING_OWNER, UPSTREAM_OWNER and
    # UPSTREAM_BRANCH values so it isn't masked in the logs.
    if 'ROT13_STAGING_OWNER' in os.environ:
        os.environ['STAGING_OWNER'] = codecs.decode(
            os.environ.get('ROT13_STAGING_OWNER'), 'rot_13')
    if 'ROT13_UPSTREAM_OWNER' in os.environ:
        os.environ['UPSTREAM_OWNER'] = codecs.decode(
            os.environ.get('ROT13_UPSTREAM_OWNER'), 'rot_13')
    if 'ROT13_UPSTREAM_BRANCH' in os.environ:
        os.environ['UPSTREAM_BRANCH'] = codecs.decode(
            os.environ.get('ROT13_UPSTREAM_BRANCH'), 'rot_13')

    if event_json:
        if 'pull_request' in event_json:
            repo_json = event_json['pull_request']['head']['repo']
            branch = event_json['pull_request']['head']['ref']
            pr = event_json['pull_request']['number']
            pr_sha = event_json['pull_request']['head']['sha']
            sender = event_json['pull_request']['user']['login']
        else:
            repo_json = event_json['repository']
            branch = event_json['ref']
            pr = None
            pr_sha = None
            sender = event_json['sender']['login']

        private_defaults = Repo(
            owner = repo_json['owner']['login'],
            repo = repo_json['name'],
            branch = branch,
            pr = pr,
            sender = sender,
        )
    else:
        private_defaults = Repo(
            owner = None,
            repo = None,
            branch = None,
            pr = None,
        )

    private = Repo(
        owner = os.environ.get(
            'PRIVATE_OWNER',
            private_defaults.owner),
        repo = os.environ.get(
            'PRIVATE_REPO',
            private_defaults.repo),
        branch = os.environ.get(
            'PRIVATE_BRANCH',
            private_defaults.branch),
        pr = private_defaults.pr,
        sender = private_defaults.sender,
    )

    staging = Repo(
        owner = os.environ.get(
            'STAGING_OWNER',
            None),
        repo = get_repo_default_name(
            'STAGING_REPO',
            private),
        branch = os.environ.get(
            'STAGING_BRANCH',
            private.branch),
    )

    upstream = Repo(
        owner = os.environ.get(
            'UPSTREAM_OWNER',
            None),
        repo = get_repo_default_name(
            'UPSTREAM_REPO',
            private),
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
    print(" Private Pull request @", pr_sha, "(", private.pr_url, ")", "created by", private.sender)
    print()

    return (private, staging, upstream, pr_sha)


def main(args):
    sys_stdout = sys.stdout
    if '--quiet' in args:
        args.remove('--quiet')
        sys.stdout = io.StringIO()
    event_json = get_event_json(sys_stdout == sys.stdout)
    private, staging, upstream, pr_sha = details(event_json)
    if args:
        for a in args:
            print(eval(a), file=sys_stdout)
    else:
        print(f"""
PRIVATE_OWNER={private.owner}
PRIVATE_REPO={private.repo}
PRIVATE_BRANCH={private.branch}
STAGING_OWNER={staging.owner}
STAGING_REPO={staging.repo}
STAGING_BRANCH={staging.branch}
UPSTREAM_OWNER={upstream.owner}
UPSTREAM_REPO={upstream.repo}
UPSTREAM_BRANCH={upstream.branch}
""".strip(), file=sys_stdout)


if __name__ == "__main__":
    sys.exit(main(list(sys.argv[1:])))
