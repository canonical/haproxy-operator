PWD:=$(shell pwd)
VIRTUAL_ENV=$(PWD)/.env
BIN=$(VIRTUAL_ENV)/bin
PATH:=$(BIN):$(PATH)

export PATH

setup:
	@virtualenv $(VIRTUAL_ENV)
	@pip install -r requirements.txt

test:
	@PYTHONPATH=hooks nosetests -s --with-coverage --cover-package=hooks --cover-erase --with-yanc --with-xtraceback tests/

auto-test:
	@yes | PYTHONPATH=hooks tdaemon --custom-args="--with-notify --no-start-message --with-yanc --with-xtraceback" --ignore-dirs=.env,.bzr

lint:
	@flake8 . --exclude=$(VIRTUAL_ENV)/*

build: setup test lint
