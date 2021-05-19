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


from github_api import get_github_json, send_github_json
from github_api import deployment as dapi
from github_api import env as genv


def update_deployment():
    event_json = genv.get_event_json()
    private, staging, upstream, pr_sha = genv.details(event_json)

    # Get the current deployments
    deployments_url = f'https://api.github.com/repos/{private.slug}/deployments'
    deployments_json = get_github_json(deployments_url, preview='ant-man-preview')

    enviro = {}
    for j in deployments_json:
        d = dapi.Deployment(**j)
        if not d.environment.startswith('Upstream PR #'):
            continue
        if d.environment in enviro:
            if d.updated_at < enviro[d.environment].updated_at:
                print()
                print(f'::group::Skipping {d.environment} updated on {d.updated_at}')
                pprint.pprint(d)
                print("::endgroup::")
                print()
                continue
        enviro[d.environment] = d

    print()
    print("::group::Current deployments")
    pprint.pprint(enviro)
    print("::endgroup::")
    print()

    pid = f'Upstream PR #{upstream.pr}'

    create_new = pid not in enviro or enviro[pid].sha != pr_sha
    if create_new:
        print()
        if pid not in enviro:
            print(f"::group::Created new deployment")
        elif enviro[pid].sha != pr_sha:
            print(f"::group::Updating deployment #{enviro[pid].id} (as {enviro[pid].sha} -> {pr_sha})")
        else:
            assert False, "????"

        new_deployment = dapi.DeploymentCreate(
            ref=pr_sha,
            auto_merge=False,
            required_contexts=[],
            payload={},
            description="",
            environment=pid,
            transient_environment=True,
            production_environment=False,
        )
        r = send_github_json(deployments_url, 'POST', new_deployment, preview='ant-man-preview')
        pprint.pprint(r)
        print("::endgroup::")
        print()
        enviro[pid] = dapi.Deployment(**r)

    print()
    print(f"::group::Current deployment #{enviro[pid].id}")
    deployment_url = f'https://api.github.com/repos/{private.slug}/deployments/{enviro[pid].id}'
    deployment = get_github_json(deployment_url, preview='ant-man-preview')
    deployment = dapi.Deployment(**deployment)
    pprint.pprint(deployment)
    print("::endgroup::")
    print()

    print()
    print(f"::group::Current deployment #{deployment.id} statuses")
    status_url = f'https://api.github.com/repos/{private.slug}/deployments/{deployment.id}/statuses'
    statuses = get_github_json(status_url, preview='ant-man-preview')
    pprint.pprint(statuses)
    print("::endgroup::")
    print()

    if not statuses:
        status_url = f'https://api.github.com/repos/{private.slug}/deployments/{deployment.id}/statuses'
        print()
        print(f"::group::Created new deployment {deployment.id} status")
        status = dapi.DeploymentStatusCreate(
            state = dapi.DeploymentState.success,
            description = f"",
            #log_url = 'https://www.google.com/',
            environment = pid,
            environment_url = f'https://github.com/{upstream.slug}/pull/{upstream.pr}',
            auto_inactive = False,
        )
        r = send_github_json(status_url, 'POST', status, preview='ant-man-preview')
        pprint.pprint(r)
        print("::endgroup::")
        print()

    return


if __name__ == "__main__":
    sys.exit(update_deployment())
