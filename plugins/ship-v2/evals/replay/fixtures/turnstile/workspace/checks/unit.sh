#!/bin/sh
# The slice's unit check: the counter's tests, standard library only.
cd "$(dirname "$0")/.." || exit 2
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src /usr/bin/python3 -m unittest discover -s tests 2>&1
