# The local lens briefs (vertical-v2; ruling E15-6)

What each local lens is asked to do, in this core's own words, read by `scope` from this file at run
time and placed at the top of the lens's mandate. v1 quoted these from another station's live text at
run time; this core states them here instead and never reads another skill's text (E15-6). The lenses a
run uses are the depth's (LEAN: `spec`, `correctness`, `seams`; DEEP adds `security` and `tests`) and
the repo's inspection sheet's passes marked `on`, less its passes marked `off` (contract section 6).
Each brief is the text under its heading, up to the next heading.

## spec

Does the built thing match the spec? Hunt for requirements silently skipped, scope quietly narrowed,
and stubs presented as finished. Walk every slice's acceptance criteria one by one against the code,
and check for files changed outside each slice's Footprint. This lens matters most, and it is the one a
generic code review misses.

## correctness

Hunt for bugs: unhandled edge cases, error paths that swallow failures, state that can fall out of
step, inputs the code never expected. Run what is runnable in your copy to prove or disprove each one.

## seams

Hunt for breaks where the new work meets what already shipped: regressions in earlier slices, broken
assumptions at a boundary, a migration or setup step that does not survive running twice, two slices
that each hold but disagree with each other.

## security

Hunt for what an attacker or a careless caller can reach: unchecked input, a secret written where it
can be read, a permission granted wider than the spec asked, a path that escapes its folder.

## tests

Hunt for what the tests do not prove: an acceptance criterion with no test, a test that passes with the
feature removed, a test that can never fail, a run that depends on the order or the clock.

## accessibility

Hunt for what a person using assistive technology, a keyboard only, or a small screen cannot do with
what was built: missing labels, focus that is lost or trapped, contrast or size the spec's users cannot
read.

## data-safety

Hunt for ways the build can lose, corrupt or leak data: a write without a backup or a rollback, a
destructive default, a migration that cannot be reversed, personal data kept longer or wider than the
spec says.
