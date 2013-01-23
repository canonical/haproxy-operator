VIRTUAL_ENV = .env
BIN = $(VIRTUAL_ENV)/bin


setup:
	@virtualenv $(VIRTUAL_ENV)
	@$(BIN)/pip install -r requirements.txt

test:
	@PYTHONPATH=hooks $(BIN)/nosetests --with-coverage --cover-package=hooks --cover-erase --with-yanc --with-xtraceback tests/

lint:
	@$(BIN)/flake8 . --exclude=./$(VIRTUAL_ENV)/*

build: setup test lint
