#!/bin/sh
# The fake claude-code launcher: the real launcher's arguments, no model (tests and `check`).
exec /usr/bin/python3 "$(dirname "$0")/fakelib.py" claude-code "$@"
