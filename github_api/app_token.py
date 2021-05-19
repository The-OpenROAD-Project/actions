#!/usr/bin/env python3

import json
import os
import pathlib
import pprint
import requests

from datetime import datetime, timedelta, timezone

import jwt


GH_APP_PRIVATE_KEY = pathlib.Path(__file__).parent / pathlib.Path("app.private-key.pem")


def get_bearer_token():
    if not GH_APP_PRIVATE_KEY.exists():
        return None

    app_id = os.environ['GITHUB_APP_ID']

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


def get_token(slug=os.environ.get('GITHUB_REPOSITORY', None)):
    assert slug is not None
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": "Bearer "+get_bearer_token(),
    }
    install_data = requests.get(
        url=f"https://api.github.com/repos/{slug}/installation",
        headers=headers,
    ).json()

    install_id = install_data['id']

    access_data = requests.post(
        url=install_data['access_tokens_url'],
        headers=headers,
    ).json()
    return access_data['token']


if __name__ == "__main__":
    print(get_token())
