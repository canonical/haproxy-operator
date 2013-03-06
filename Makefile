PWD := $(shell pwd)
HOOKS_DIR := $(PWD)/hooks
TEST_PREFIX := PYTHONPATH=$(HOOKS_DIR)
TEST_DIR := $(PWD)/tests
CHARM_DIR := $(PWD)
EXCLUDED_LINT_DIRS := $(PWD)/lib
PYTHON := /usr/bin/env python


build: sourcedeps test lint proof

proof:
	@echo Proofing charm...
	@charm proof $(PWD) && echo OK

test:
	@echo Starting tests...
	@CHARM_DIR=$(CHARM_DIR) $(TEST_PREFIX) nosetests $(TEST_DIR)

lint:
	@echo Checking for Python syntax...
	@flake8 $(PWD) --ignore=E123 --exclude=$(EXCLUDED_LINT_DIRS) && echo OK

sourcedeps: $(PWD)/config-manager.txt
	@echo Updating source dependencies...
	@$(PYTHON) /usr/lib/config-manager/cm.py update $(PWD)/config-manager.txt

charm-payload: sourcedeps
