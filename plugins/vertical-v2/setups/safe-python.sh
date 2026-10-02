#!/bin/sh
set -eu
[ "$#" -ge 1 ] || exit 2
exec env -u TMPDIR -u TEMP -u TMP PYTHONDONTWRITEBYTECODE=1 "${SAFE_PYTHON:-/usr/bin/python3}" - \
  "${TMPDIR-}" "${TEMP-}" "${TMP-}" "$@" <<'PY'
import os, runpy, sys
for key, value in zip(("TMPDIR", "TEMP", "TMP"), sys.argv[1:4]):
    if value:
        os.environ[key] = value
sys.argv = sys.argv[4:]
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
runpy.run_path(sys.argv[0], run_name="__main__")
PY
