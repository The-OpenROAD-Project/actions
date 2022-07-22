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

include common/config.mk

APPS=pull-request-sender pull-request-sender-auth-check

env:
	virtualenv env
	source env/bin/activate; pip install -r pull-request-sender/requirements.txt
	source env/bin/activate; pip install -r pull-request-sender-auth-check/requirements.txt

enter:
	source env/bin/activate; bash

build:
	for A in $(APPS); do (cd $$A; make build); done

deploy:
	make build
	(cd common; yes | gcloud --project=$(PROJECT_ID) datastore indexes create index.yaml)
	for A in $(APPS); do (cd $$A; make deploy); done
