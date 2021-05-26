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


import os
from collections import namedtuple

import tokenlib


_PRInfo = namedtuple("PRInfo", "user org repo pr rev")


class PRInfo(_PRInfo):

    @classmethod
    def _tm(cls, tm_store=[]):
        if not tm_store:
            tm_store.append(SimpleTokenManager(
                secret=os.environ['CLIENT_TOKEN']))
        return tm_store[0]

    @property
    def pr_url(self):
        """
        >>> i = PRInfo.parse("mithro:The-OpenROAD-Project/OpenROAD/2@main")
        >>> i.pr_url
        'https://github.com/The-OpenROAD-Project/OpenROAD/pull/2'
        """
        return f"https://github.com/{self.org}/{self.repo}/pull/{self.pr}"

    @property
    def auth_url(self):
        return f'https://pr.gha.openroad.tools/auth?state='+self.to_token()

    @property
    def hook_url(self):
        return f'https://a.gha.openroad.tools/hook?state='+self.to_token()

    @property
    def revoke_url(self):
        return f'https://a.gha.openroad.tools/revoke?state='+self.to_token()

    @property
    def slug(self):
        return f"{self.org}/{self.repo}"

    @classmethod
    def check(cls, s):
        """
        >>> PRInfo.check("mithro:The-OpenROAD-Project/OpenROAD/2@main")
        True
        >>> PRInfo.check("mithro:The-OpenROAD-Project/OpenROAD/2@")
        False
        """
        try:
            user, org, repo, pr, rev = cls.parse(s)
            assert user, s
            assert org,  s
            assert repo, s
            assert pr,   s
            assert rev , s
            return True
        except Exception as e:
            return False

    @classmethod
    def from_token(cls, estate):
        assert estate is not None, estate
        state = cls._tm().parse_token(estate)
        return cls.parse(state)

    def to_token(self, salt=None):
        """
        >>> i = PRInfo.parse("mithro:The-OpenROAD-Project/OpenROAD/2@main")
        >>> t = i.to_token(b'AAA')
        >>> t
        'QUFBbWl0aHJvOlRoZS1PcGVuUk9BRC1Qcm9qZWN0L09wZW5ST0FELzJAbWFpbtXQMDVIcDMABpYwq0bR16ASrpgL6HVjgv8ibtahoZzg'
        >>> PRInfo.from_token(t)
        PRInfo(user='mithro', org='The-OpenROAD-Project', repo='OpenROAD', pr=2, rev='main')
        >>> t = i.to_token(b'AAB')
        >>> t
        'QUFCbWl0aHJvOlRoZS1PcGVuUk9BRC1Qcm9qZWN0L09wZW5ST0FELzJAbWFpbgwv3YQAVjJL-ewHxQqxEA8aBzOSopyLwO5nW9IUnlma'
        >>> PRInfo.from_token(t)
        PRInfo(user='mithro', org='The-OpenROAD-Project', repo='OpenROAD', pr=2, rev='main')
        """
        return self._tm().make_token(str(self), salt=salt)

    @classmethod
    def from_request(cls, r):
        estate = r.args.get('state')
        assert estate is not None, r.args
        return cls.from_token(estate)

    @classmethod
    def from_json(cls, j):
        return cls(
            j['user']['login'],
            *j['base']['repo']['full_name'].split('/'),
            j['number'],
            j['head']['sha'])

    @classmethod
    def parse(cls, s):
        """
        >>> PRInfo.parse("mithro:The-OpenROAD-Project/OpenROAD/2@main")
        PRInfo(user='mithro', org='The-OpenROAD-Project', repo='OpenROAD', pr=2, rev='main')

        """
        assert ':' in s, s
        assert '/' in s, s
        assert '@' in s, s
        rest = s

        user, rest = rest.split(':', maxsplit=1)
        org,  repo, rest = rest.split('/', maxsplit=2)
        pr, rev  = rest.split('@', maxsplit=1)
        pr = int(pr)
        return cls(user, org, repo, pr, rev)

    def __str__(self):
        """

        >>> str(PRInfo('mithro', 'The-OpenROAD-Project', 'OpenROAD', 2, 'main'))
        'mithro:The-OpenROAD-Project/OpenROAD/2@main'

        >>> str(PRInfo('mithro', 'The-OpenROAD-Project', 'OpenROAD', '2', 'main'))
        'mithro:The-OpenROAD-Project/OpenROAD/2@main'

        """
        return f"{self.user}:{self.org}/{self.repo}/{self.pr}@{self.rev}"


class SimpleTokenManager(tokenlib.TokenManager):
    salt_length = 3

    def make_token(self, data, salt=None):
        """Generate a new token embedding the given dict of data.

        The token is a JSON dump of the given data along with an expiry
        time and salt.  It has a HMAC signature appended and is b64-encoded
        for transmission.
        """
        if salt is None:
            salt = os.urandom(self.salt_length)
        else:
            assert len(salt) == self.salt_length, self.salt_length
        payload = salt+data.encode("utf8")
        sig = self._get_signature(payload)
        assert len(sig) == self.hashmod_digest_size
        return tokenlib.utils.encode_token_bytes(payload + sig)

    def parse_token(self, token, now=None):
        """Extract the data embedded in the given token, if valid.

        The token is valid if it has a valid signature and if the embedded
        expiry time has not passed.  If the token is not valid then this
        method raises ValueError.
        """
        # Parse the payload and signature from the token.
        try:
            decoded_token = tokenlib.utils.decode_token_bytes(token)
        except (TypeError, ValueError) as e:
            raise tokenlib.errors.MalformedTokenError(str(e))
        payload = decoded_token[:-self.hashmod_digest_size]
        sig = decoded_token[-self.hashmod_digest_size:]
        # Carefully check the signature.
        # This is a deliberately slow string-compare to avoid timing attacks.
        # Read the docstring of strings_differ for more details.
        expected_sig = self._get_signature(payload)
        if tokenlib.utils.strings_differ(sig, expected_sig):
            raise tokenlib.errors.InvalidSignatureError()
        # Only decode *after* we've confirmed the signature.
        # This should never fail, but well, you can't be too careful.
        return payload[self.salt_length:].decode('utf-8')


if __name__ == "__main__":
    os.environ['CLIENT_TOKEN'] = 'doctest'
    import doctest
    doctest.testmod()
