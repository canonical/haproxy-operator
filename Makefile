test:
	@PYTHONPATH=hooks nosetests --with-coverage --cover-package=hooks --cover-erase --with-yanc --with-xtraceback tests/

lint:
	@flake8 .

build: test lint
