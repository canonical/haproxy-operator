PWD := $(shell pwd)
HOOKS_DIR := $(PWD)/hooks
TEST_PREFIX := PYTHONPATH=$(HOOKS_DIR)
TEST_DIR := $(PWD)/tests
CHARM_DIR := $(PWD)
EXCLUDED_LINT_DIRS := $(PWD)/.env/*


build: test lint

test:
	@echo Starting tests...
	@CHARM_DIR=$(CHARM_DIR) $(TEST_PREFIX) nosetests $(TEST_DIR)

lint:
	@echo Checking for Python syntax...
	@flake8 $(PWD) --ignore=E123 --exclude=$(EXCLUDED_LINT_DIRS)