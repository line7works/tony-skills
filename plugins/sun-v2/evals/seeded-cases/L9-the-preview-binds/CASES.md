# L9-the-preview-binds: cases

Family L9 of the E16 seeded cases (lane contract section 12, row "L9 the preview binds"; the lifecycle frame, slice 1). 5 cases, ids exact. Facts only: what each case holds. Nothing here states an outcome.

Build: `python3 build.py --out <dir>`. `../observe.py --out <dir> --all` drives each case.

## Shared shape

The fixture machine and the eight fake rows of the reference run (case 04: a build and an owner step in read-back mode). Steps: a first look, the go, and what the case names.

## L9-01-clean

Nothing planted.

## L9-02-a-manifest-changed-after-the-go

The go is killed after the build's completion record; the manifest's file is then rewritten with another description; a resume follows.

## L9-03-an-operation-outside-it

The go is killed after the build's completion record; an operation the preview did not show is then written into the manifest's file; a status summons follows.

## L9-04-an-owner-operation

A row whose step only the owner can take, in read-back mode. Steps: the look, the go, a status summons, the owner changing the fake provider's state by hand, a status summons.

## L9-05-a-go-on-another-manifest

The go names a manifest hash that is not the previewed manifest's.
