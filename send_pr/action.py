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
import sys


sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))


import github_api
from github_api import get_github_json, send_github_json
from github_api import env as genv


def send_pr():
    github_api.TOKEN_ENV_NAME = 'STAGING_GITHUB_TOKEN'
    event_json = genv.get_event_json()
    private, staging, upstream, pr_sha = genv.details(event_json)

    # Figure out if there are any pull requests associated with the sha at the
    # moment.
    pr_api_url = f'https://api.github.com/repos/{staging.slug}/commits/{pr_sha}/pulls'
    prs_json = get_github_json(pr_api_url, preview="groot-preview")

    print()
    print(f"::group::Current pull requests from {staging.slug} for {pr_sha}")
    pprint.pprint(prs_json)
    print("::endgroup::")
    print()

    if not prs_json:
        # Need to create a new pull request.
        pr_api_url = f'https://api.github.com/repos/{upstream.slug}/pulls'

        create_pr_json = {
            "base": upstream.branch,
            "head": f"{staging.owner}:{staging.branch}",
            "title": event_json["pull_request"]["title"],
            "body": event_json["pull_request"]["body"],
            "maintainer_can_modify": True,
            "draft": False,
        }
        r = send_github_json(pr_api_url, "POST", create_pr_json)
        print(f"::group::Created pull request from {staging.slug} {staging.branch} to {upstream.slug}")
        pprint.pprint(r)
        print("::endgroup::")
        print()
        prs_json.append(r)

        new_pr_number = r.get("number") # Get the PR number directly from the response
        original_pr_author = event_json["pull_request"]["user"]["login"]
        assign_user_to_pr(upstream.slug, new_pr_number, original_pr_author)
    else:
        print()
        print("Pull request already existed!")
        print()

    upstream.pr = prs_json[-1]["number"]

    print()
    print("Private PR:", private.pr, private.pr_url)
    print("Upstream PR:", upstream.pr, upstream.pr_url)

    print("::set-output name=pr::"+str(upstream.pr))

    return

def assign_user_to_pr(repo_slug, pr_number, username):
    """Assigns a user to a pull request."""
    assignees_url = f"https://api.github.com/repos/{repo_slug}/issues/{pr_number}/assignees"

    assignees_data = {
        "assignees": [username]
    }
    try:
        r = send_github_json(assignees_url, "POST", assignees_data)
        print(f"::group::Assigned {username} to PR #{pr_number} in {repo_slug}")
        pprint.pprint(r)
        print("::endgroup::")
    except Exception as e:
        print(f"::error::Failed to assign {username} to PR #{pr_number}: {e}")

if __name__ == "__main__":
    sys.exit(send_pr())
