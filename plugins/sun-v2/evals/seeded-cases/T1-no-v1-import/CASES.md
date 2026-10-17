# T1-no-v1-import: cases

Family T1 of the E16 seeded cases (lane contract section 12, row "T1 no v1 import"; ruling E16-16). 4 cases, ids exact. Facts only: what each case holds. Nothing here states an outcome.

Build: `python3 build.py --out <dir>`. `../observe.py --out <dir> --all` drives each case.

## Shared shape

The scan of `lifecycle/scripts/tests/test_no_v1_import.py` over this plugin, or over a scratch copy of it with the case's plant appended to one file. The plant's text is assembled from parts, so no case file names a v1 folder.

## T1-01-clean

No plant; the plugin itself is scanned.

## T1-02-a-v1-path

`lifecycle/scripts/sun_core/facts.py` gains a line naming a file under the v1 plugin's folder.

## T1-03-a-deference

`skills/sunset-v2/SKILL.md` gains a sentence deferring to the v1 skill as law where this skill is silent.

## T1-04-a-subprocess-that-names-a-v1-skill

`lifecycle/scripts/sun.py` gains a subprocess call whose arguments name a v1 skill as a slash command.
