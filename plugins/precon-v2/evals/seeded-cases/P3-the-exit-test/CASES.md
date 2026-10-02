# P3-the-exit-test: cases

Family P3 of the E14 seeded cases (lane contract section 14, row "the exit test"; precon-v2). 4 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

The workspace holds `README.md` and the scope doc `docs/scope/2026-09-20-turnstile.md` (P1's). The run builds one readers request per named row for the exit test: the scope doc as the single document, profile `starved`.

## P3-01-clean

The input's `owner_word` names the row `gpt-astra`. Requests are built for `claude-session` and `gpt-astra`.

## P3-02-outside-no-word

The input carries no `owner_word`. A request is built for `gpt-astra`.

## P3-03-claude-row-named

The input's `owner_word` names `claude-session`. A request is built for `claude-session`.

## P3-04-word-names-another-row

The input's `owner_word` names `gemini`. Requests are built for `gpt-astra` and `gemini`.
