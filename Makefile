PWD := $(shell pwd)
SOURCEDEPS_DIR ?= $(shell dirname $(PWD))/.sourcecode
HOOKS_DIR := $(PWD)/hooks
TEST_PREFIX := PYTHONPATH=$(HOOKS_DIR)
TEST_DIR := $(PWD)/hooks/tests
CHARM_DIR := $(PWD)
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
	@flake8 $(HOOKS_DIR) --ignore=E123 && echo OK

sourcedeps: $(PWD)/config-manager.txt
	@echo Updating source dependencies...
	@$(PYTHON) cm.py -c $(PWD)/config-manager.txt \
		-p $(SOURCEDEPS_DIR) \
		-t $(PWD)

charm-payload: sourcedeps
