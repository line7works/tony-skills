# L6-resume: cases

Family L6 of the E16 seeded cases (lane contract section 12, row "L6 resume"; the lifecycle frame, slice 1). 5 cases, ids exact. Facts only: what each case holds. Nothing here states an outcome.

Build: `python3 build.py --out <dir>`. `../observe.py --out <dir> --all` drives each case.

## Shared shape

The fixture machine and the eight fake rows of the reference run. Steps: a first look, the go, and what the case names after it.

## L6-01-clean

Nothing planted. The unkilled run: the reference.

## L6-02-a-kill-at-every-point-of-every-operation

The kill sweep (`lifecycle/scripts/tests/killlib.py`): the go is started once per write boundary of the reference run's go, each time on a fixture machine of its own, and ends itself there with a real SIGKILL, a write not yet synced lost with it; a status summons and a resume on its position follow each kill.

## L6-03-a-lost-create-response

The fake hosting tool makes the thing and its process ends before it answers. Two resumes follow the go.

## L6-04-a-torn-last-line

The go is killed after the start record of the swap, with the kill taking half of an append that was not yet synced; a status summons and a resume follow.

## L6-05-two-runs-at-once

The go is killed after the create's start record; then, while another holder has the project's lock, a second first look of the same project is summoned.
