#!/bin/sh
# The fake codex launcher: the real launcher's arguments, no model (tests and `check`).
exec /usr/bin/python3 "$(dirname "$0")/fakelib.py" codex "$@"
