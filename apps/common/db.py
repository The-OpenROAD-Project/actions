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
import pprint
import requests
import urllib


from google.cloud import ndb


class Token(ndb.Model):
    login = ndb.StringProperty(indexed=True, required=True)
    access_token = ndb.StringProperty(required=True)
    expires_in = ndb.IntegerProperty(required=True)
    refresh_token = ndb.StringProperty(required=True)
    refresh_token_expires_in = ndb.IntegerProperty(required=True)
    token_type = ndb.StringProperty(required=True)
    updated = ndb.DateTimeProperty(auto_now=True)
    created = ndb.DateTimeProperty(auto_now_add=True)

    def to_table(self):
        c = (datetime.datetime.utcnow() - self.created).seconds
        u = (datetime.datetime.utcnow() - self.updated).seconds
        ein = self.created + datetime.timedelta(seconds=self.expires_in)
        rin = self.created + datetime.timedelta(seconds=self.refresh_token_expires_in)
        return f"""\
  <table>
   <tr><th>Login             </th><td>{self.login}                        </td><td>              </td></tr>
   <tr><th>Created           </th><td>{c}s ago                            </td><td>{self.created}</td></tr>
   <tr><th>Last updated      </th><td>{u}s ago                            </td><td>{self.updated}</td></tr>
   <tr><th>Auth Expires In   </th><td>t + {self.expires_in}s              </td><td>{ein}         </td></tr>
   <tr><th>Refresh Expires In</th><td>t + {self.refresh_token_expires_in}s</td><td>{rin}         </td></tr>
   <tr><th>Type              </th><td>{self.token_type}                   </td><td>              </td></tr>
  </table>
"""

    def to_html(self):
        return f"""\
<html>
 <body>
{self.to_table()}
 </body>
</html>
"""

    @classmethod
    def latest(cls, login):
        with client.context():
            q = cls.query().filter(cls.login==login).order(-cls.created)
            for t in q:
                return t

    @classmethod
    def delete(cls, login):
        with client.context():
            q = cls.query().filter(cls.login==login).order(-cls.created)
            for t in q:
                t.key.delete()

    @classmethod
    def from_response(cls, login, d):
        od = dict(urllib.parse.parse_qsl(d.text))

        if 'error' in od:
            ods = pprint.pformat(od)
            return f"""\
<html>
 <body>
  <a href="{od['error_uri']}">{od['error_description']}</a>
  <br>
  <pre>{ods}</pre>
 </body>
</html>
"""
        # Use the token to figure out the username of the user associated with the
        # token.
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"{od['token_type']} {od['access_token']}",
        }
        ud = requests.get(
            url="https://api.github.com/user",
            headers=headers,
        ).json()
        assert ud['login'] == login, (ud['login'], login)

        od['login'] = login
        return cls.from_json(od)

    @classmethod
    def from_json(cls, od):
        assert 'access_token' in od, od
        assert 'token_type' in od, od
        assert 'expires_in' in od, od
        od['expires_in'] = int(od['expires_in'])
        assert 'refresh_token' in od, od
        assert 'refresh_token_expires_in' in od, od
        od['refresh_token_expires_in'] = int(od['refresh_token_expires_in'])
        return cls(**od)


client = ndb.Client()
