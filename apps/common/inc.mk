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

MAKE_DIR := $(realpath $(dir $(lastword $(MAKEFILE_LIST))))

include $(MAKE_DIR)/config.mk

SRCS=\
     ../common/Dockerfile \
     ../common/.dockerignore \
     ../common/db.py \
     ../common/utils.py \
     *.py \
     *.txt \
     ../../github_api

PYTHONPATH=$(abspath $(PWD)/../common):$(abspath $(PWD)/../../)
export PYTHONPATH

BUILD_DIR=$(PROJECT_NAME)-build

build:
	rm -rf $(BUILD_DIR)
	mkdir $(BUILD_DIR)
	cp -a $(SRCS) ./$(BUILD_DIR)/
	find $(BUILD_DIR) -name '*.pem' -delete
	find $(BUILD_DIR) -name '*.pyc' -delete
	find $(BUILD_DIR) -name '.*.sw*' -delete
	find $(BUILD_DIR) -type d -empty -delete
	find $(BUILD_DIR) | sort
	cd $(BUILD_DIR); gcloud --project=$(PROJECT_ID) \
		builds submit \
		--tag gcr.io/$(PROJECT_ID)/$(PROJECT_NAME)

.PHONY: build

SECRETS_ENV=CLIENT_ID CLIENT_SECRET APP_ID
SECRETS_CENV=CLIENT_TOKEN

SECRETS_CMDLINE_ENV=$(shell echo $(SECRETS_ENV) | sed -e's/\([^ ]\+\) \?/\1=$(SECRETS_PREFIX)_\1:latest,/g' -e's/,$$//')
SECRETS_CMDLINE_CENV=$(shell echo $(SECRETS_CENV) | sed -e's/\([^ ]\+\) \?/,\1=COMMON_\1:latest,/g' -e's/,$$//')
SECRETS_CMDLINE_PEM=,/keys/app.private-key.pem=$(SECRETS_PREFIX)_CLIENT_KEY:latest

deploy:
	gcloud --project=$(PROJECT_ID) beta \
		run deploy \
		$(PROJECT_NAME) \
		--image gcr.io/$(PROJECT_ID)/$(PROJECT_NAME) \
		--platform managed --region=$(REGION) \
		--allow-unauthenticated \
		--set-env-vars PROJECT_ID=$(PROJECT_ID),CLIENT_KEY=/keys/app.private-key.pem \
		--service-account=$(SERVICE_ACCOUNT)@$(PROJECT_ID).iam.gserviceaccount.com \
		--set-secrets=$(SECRETS_CMDLINE_ENV)$(SECRETS_CMDLINE_CENV)$(SECRETS_CMDLINE_PEM)

.PHONY: deploy

DATASTORE_EMULATOR_HOST=localhost:8081
db:
	gcloud beta emulators datastore start
