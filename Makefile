PWD := $(shell pwd)
SOURCEDEPS_DIR ?= $(shell dirname $(PWD))/.sourcecode
HOOKS_DIR := $(PWD)/hooks
TEST_PREFIX := PYTHONPATH=$(HOOKS_DIR)
TEST_DIR := $(PWD)/hooks/tests
CHARM_DIR := $(PWD)
PYTHON := /usr/bin/env python


build: test lint proof

proof:
	@echo Proofing charm...
	@charm proof

.venv:
	sudo apt-get install -y flake8 python-apt python-virtualenv python-jinja2 python-mock python-yaml python-testtools python-nose python-yaml python-flake8
	virtualenv .venv --system-site-packages
	.venv/bin/pip install bundletester

test: .venv
	@echo Starting tests...
	@CHARM_DIR=$(CHARM_DIR) $(TEST_PREFIX) nosetests -s $(TEST_DIR)

lint: .venv
	@echo Checking for Python syntax...
	@python -m flake8 $(HOOKS_DIR) --ignore=E123 --exclude=$(HOOKS_DIR)/charmhelpers

sourcedeps:
	@echo Updating source dependencies...
	@mkdir -p $(PWD)/build/charm-helpers/tools/charm_helpers_sync
	@curl -sL https://github.com/juju/charm-helpers/raw/master/tools/charm_helpers_sync/charm_helpers_sync.py \
	    -o $(PWD)/build/charm-helpers/tools/charm_helpers_sync/charm_helpers_sync.py
	@$(PYTHON) build/charm-helpers/tools/charm_helpers_sync/charm_helpers_sync.py \
		-c charm-helpers.yaml \
		-d hooks/charmhelpers
	@echo Do not forget to commit the updated files if any.

.PHONY: revision proof test lint sourcedeps charm-payload
