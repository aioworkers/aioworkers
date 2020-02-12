TARGETS=aioworkers tests

test:
	isort -rc $(TARGETS)
	flake8 $(TARGETS)
	mypy $(TARGETS)
	pytest

test-all:
	tox

docs:
	cd docs && $(MAKE) html

aioworkers/version.py:
	echo "__version__ = '$(shell git describe --tags)'" > $@

release:
	python setup.py sdist upload

install:
	python setup.py install
