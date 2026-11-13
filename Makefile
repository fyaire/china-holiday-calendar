.PHONY: build check test

build:
	python3 scripts/build.py

check:
	python3 scripts/build.py --check

test:
	python3 -m unittest discover -s tests -v

