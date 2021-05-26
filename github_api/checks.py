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


import enum
import json
import pprint
import dataclasses

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


"""
Small library for working with GitHub Check Runs / Suites.
"""


def datetime_field():
    return field(
#        metadata=config(
#            encoder=toisoformat,
#            decoder=fromisoformat,
#        ),
        default = None,
    )


# -------------------------------------------------------------------
# Info for an existing check run.
# -------------------------------------------------------------------


# Annotations
# https://api.github.com/repos/octocat/hello-world/check-runs/42/annotations
# -------------------------------------------------------------------


@enum.unique
class CheckRunAnnotationLevel(enum.Enum):
    notice      = 'notice'
    warning     = 'warning'
    failure     = 'failure'


@dataclass
class CheckRunAnnotation:
    path: str
    start_line: int
    end_line: int

    annotation_level: CheckRunAnnotationLevel
    message: str
    title: str
    raw_details: str

    start_column: Optional[int] = None
    end_column: Optional[int] = None


@enum.unique
class CheckStatus(enum.Enum):
    queued      = 'queued'
    in_progress = 'in_progress'
    completed   = 'completed'


# Check Runs
# https://api.github.com/repos/octocat/hello-world/check-runs/42
# -------------------------------------------------------------------


@enum.unique
class CheckConclusion(enum.Enum):
    action_required = 'action_required'
    cancelled       = 'cancelled'
    failure         = 'failure'
    neutral         = 'neutral'
    success         = 'success'
    skipped         = 'skipped'
    stale           = 'stale'
    timed_out       = 'timed_out'


@dataclass
class CheckRunOutput:
    title: Optional[str] = None
    summary: Optional[str] = None
    text: Optional[str] = None

    annotations_count: int = 0
    annotations_url: Optional[str] = None


@dataclass
class CheckSuite:
    id: int


@dataclass
class CheckRun:

    id: int
    node_id: str

    name: str
    head_sha: str

    details_url: str
    external_id: str

    output: CheckRunOutput

    url: str
    html_url: str

    #app: dict
    check_suite: Optional[CheckSuite] = None

    status: Optional[CheckStatus] = None
    started_at: Optional[datetime] = datetime_field()
    completed_at: Optional[datetime] = datetime_field()
    conclusion: Optional[CheckConclusion] = None

    pull_requests: Optional[list[dict]] = None

    @staticmethod
    def _pprint(p, object, stream, indent, allowance, context, level):
        p._pprint_dict(dataclasses.asdict(object), stream, indent, allowance, context, level)


pprint.PrettyPrinter._dispatch[CheckRun.__repr__] = CheckRun._pprint


# -------------------------------------------------------------------
# Creating a check run.
# -------------------------------------------------------------------


@dataclass
class CheckRunCreateAction:
    label: str
    description: str
    identifier: str


@dataclass
class CheckRunCreateOutputImage:
    alt: str
    image_url: str
    caption: str


@dataclass
class CheckRunCreateOutput:
    title: str      # Required
    summary: str    # Required
    text: str

    annotations: list[CheckRunAnnotation] = field(default_factory=list)
    images: list[CheckRunCreateOutputImage] = field(default_factory=list)


@dataclass
class CheckRunCreate:
    # Header: accept = "application/vnd.github.v3+json"
    # URL: owner: str = ""
    # URL: repo: str = ""
    # URL: check_run_id: str = ""

    name: str
    head_sha: str

    details_url: Optional[str] = None
    external_id: Optional[str] = None

    status: Optional[CheckStatus] = CheckStatus.queued
    started_at: Optional[datetime] = datetime_field()

    conclusion: Optional[CheckConclusion] = None
    completed_at: Optional[datetime] = datetime_field()

    output: Optional[CheckRunCreateOutput] = None

    actions: list[CheckRunCreateAction] = field(default_factory=list)

    @staticmethod
    def _pprint(p, object, stream, indent, allowance, context, level):
        p._pprint_dict(dataclasses.asdict(object), stream, indent, allowance, context, level)


pprint.PrettyPrinter._dispatch[CheckRunCreate.__repr__] = CheckRunCreate._pprint


if __name__ == "__main__":
    import doctest
    doctest.testmod()
