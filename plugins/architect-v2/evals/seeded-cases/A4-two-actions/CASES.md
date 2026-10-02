# A4-two-actions: cases

Family A4 of the E14 seeded cases (lane contract section 14, row "two actions"; architect-v2). 3 cases, catalog order, ids exact. Facts only: what each case holds and what its recorded answer carries. Nothing here states an outcome.

Build: `sh ../../../setups/safe-python.sh build.py --out <dir>`. `build.py --list` prints the ids. `../observe.py` drives each case.

## Shared shape

LANE CASES (render-visual and record-publish are lane A's). The workspace holds the scope doc and the architecture doc `docs/architecture/2026-09-21-turnstile.md`, whose `Artifact:` line reads `https://example.invalid/artifact/turnstile`. The recorded answer carries `publish` (boolean) and `publish_url` (the URL the executor's publish returned, or null).

## A4-01-clean (lane)

`publish` is true and `publish_url` equals the doc's recorded URL.

Recorded answer: `answers/A4-01-clean.json`.

## A4-02-publish-false (lane)

`publish` is false and `publish_url` is null; the neutral input carries `station_publish: false`.

Recorded answer: `answers/A4-02-publish-false.json`.

## A4-03-no-url-returned (lane)

`publish` is true and `publish_url` is null: the publish returned no URL.

Recorded answer: `answers/A4-03-no-url-returned.json`.
