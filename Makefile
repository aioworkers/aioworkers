
test:
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
