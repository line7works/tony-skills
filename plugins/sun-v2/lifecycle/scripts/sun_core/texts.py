"""The tool's own fixed text (the frame's SEC-1: safe by where it came from).

Every sentence the tool prints before its startup checks have passed is one of these, with at most
run ids, file names and the tool's own folder in its slots (SEC-12, "Before the startup checks pass").
Nothing here is built from a journal, a manifest or any other record.
"""

TOOL = "sun-v2"
INTERFACE_VERSION = 1

# The fixed words of withholding (SEC-12): they stand in the place of a value a run has caught.
WITHHELD = "[withheld: a value this tool may not show]"

# Early refusals and stops: the failed check is named, and nothing else is said (RUN-12).
GATE = {
    "vault-settings": "The gate failed: the settings file names no vault. Nothing was created.",
    "vault-missing": "The gate failed: there is no vault at the place the settings file names. Nothing was created.",
    "vault-marker": "The gate failed: the vault lacks its marker file, so it is a stub. Nothing was created.",
    "vault-projects": "The gate failed: the vault has its marker file and no projects folder. Nothing was created.",
    "vault-synced": "The gate failed: the vault lies inside a synced folder. Nothing was created.",
    "keying-missing": "The gate failed: the file that keys the lock fingerprints is missing while a lock or the record of open runs exists.",
    "keying-wide": "The gate failed: the file that keys the lock fingerprints is readable by others.",
}
KEYING_PLACE = "The keying file is kept at: "
RUN_ON_RECORD = "A run is on record: "
RUN_ON_RECORD_UNNAMED = "A run is on record which the tool cannot name."
LOCKS_PLACE = "The lock files and the record of open runs are kept at: "
ID_IN_FILE = "; its id is in the record of the file named "
# The one sentence where a record of the tool's own cannot be read (SEC-12; the owner's ruling A40): every start prints
# it and nothing else, the same whichever of the three failed; it holds no file name and no path.
RECORD_UNREADABLE = "The tool stops: a record it keeps in its own folder cannot be read. Nothing was done; mend that record and start again."
# The three ways on at the keying value's refusal (RUN-2; the owner's ruling A43): each a step of his, printed after the
# listing, all three whichever of the two the gate found; none holds a file's name, a path or a run's id.
WAYS_ON = (
    "If the file that keys the lock fingerprints is readable by others: make it readable by its owner alone, and summon again.",
    "If that file is missing: put it back from a copy of your own, and summon again.",
    "If you have no copy, the one way left is a decision that is yours alone: end by hand each run listed above, remove "
    "the lock files and the record of open runs yourself, and summon again; the tool then makes a new value, and from "
    "then on it sees none of those runs: it can neither resume nor close them, and it does not refuse a new run on a "
    "project one of them had open.",
)
NAME_REFUSED = "Refused: a name this summons carries may not be used. Nothing of it was written and no lock was taken."
LOCK_HELD = "Refused: the lock of this project is held by a run: "
LOCK_HELD_NO_ID = "Refused: the lock of this project is held, and its record names no run yet."
RUN_OPEN = "Refused: a run is open on this project: "
RUN_OPEN_WAYS = "An open run may be resumed, re-planned or closed."
RUNDIR_STOP = {
    "permissions": "Stopped: the run directory, or something in it, is not owner-only. Nothing was read from its records.",
    "chain": "Stopped: the journal of the run does not read back whole. Nothing was read from its records.",
    "disproof-unreadable": "Stopped: a record of a withheld value in the run directory cannot be read. Nothing was read from its records.",
    "missing": "Stopped: the run directory is not there. Nothing was read from its records.",
}
NOTHING_TO_RESUME = "Refused: no run is open on this project, so there is nothing to continue."
WORD_NEEDED = "No word was given for this run, or the form it answers is no longer the latest: the status form is rendered and nothing was done."
REPLAN_NEEDED = "The accounts, the capabilities or the machine locations read now are not the ones the plan holds: a re-plan is needed. Nothing was done."
CLOSED_NEVER_RESUMES = "Refused: this run has ended, and an ended run is not continued."
VALUE_WITHHELD_STOP = "Stopped: a record would have carried a value this tool may not show, and it was not written."

ENDINGS = ("complete", "ended with exceptions", "waiting", "stopped", "closed")
PRE_GO_ENDINGS = ("preview", "refused")

CUE_LINE = {"sunrise": "S U N R I S E", "sunset": "S U N S E T", "restore": "R E S T O R E"}

THE_RUN = "The run: "
MORE_THAN_ONE_OPEN = "Refused: the names this summons carries belong to more than one open run."
USAGE = "usage error: an argument is missing or malformed; see --help. Nothing was read of the project and nothing was created."
DEFECT = "the command ended on a defect of its own: "
# The tool's own failure line (RUN-1, SEC-12; A52, A53): its first code ran and made the withheld read, and a file of
# the tool outside that code is missing or cannot be loaded, or a later part failed. Printed under the withheld read.
FAILURE = "The tool cannot go on: a file of its own is missing or broken, or a part of it failed. Nothing more was done."
# The identity answer (SEC-12, A54): the tool's own fixed words where no repository holds its files in a commit, and
# where a git child gave no answer of the commit.
NO_COMMIT = "no commit holds these files"

# SEC-10's check before a commit and before a push (A87, A89): a hit stops the run, names the file and shows nothing.
SEC10_HIT = "a check before a commit or a push found a value that may not be committed"
SEC10_IGNORE = "a check before a commit cannot prove that git ignores a file that holds secrets"
SEC10_FILE = "the file: "
NO_ANSWER = "git gave no answer"
# A read the go makes at its start (RUN-10 (b)'s identity read) refused by the runner (SEC-3, A53): no changed context,
# and no look again, which would meet the same refusal.
REFUSED_READ_AT_GO = "Refused: the runner refused a read this go makes at its start ({reason}: the identity read of {provider}). No go was recorded; a new look would meet the same refusal."
CONTEXT_CHANGED_BEFORE_GO = "Refused: the accounts, the capabilities or the machine locations read now are not the ones the preview was made from. Look again."
MANIFEST_ALTERED = "Stopped: the manifest in force no longer gives the hash its go was recorded with. Nothing was done."
NOT_THE_PREVIEWED = "Refused: the manifest named with this go is not the one the latest preview showed. Nothing was done."
ALREADY_HAS_GO = "Refused: this run already has its go on that manifest. Resume it, or re-plan it."
INPUT_REFUSED = "Refused: an input may not be used. It was stored nowhere."
INPUT_REFUSED_REPLAN = "Stopped: an input of the re-plan may not be used. The manifest in force is unchanged."
QUESTIONS = "An answer the look needs is lacking; nothing is approved. The questions:"
PLANNING_STOP = "The look ended before any preview. Each cause:"
# G20-3: a type off the lane's kept list, refused before the look's reads; an answer his question's declared validator refuses
TYPE_NOT_KEPT = "the project type {type} is not one this tool keeps; the kept types: {kept}. Summon again with one of them."
PART_REFUSED = "A value filled into row {row} fails its check, {validator}; summon again with another."
ANSWER_REFUSED = "{question} (the answer given fails its check, {validator}; answer again)"
# G20-7 (A150, the control room's reading): a staged document chosen in the look, by the tool's own numbers and his date
CHOOSE_STAGED = ("Several staged documents match for {fact}; answer with the number of the one to take, as answers.{fact}: "
                 "{listing}")
DATE_STAGED = ("The staged document for {fact} has no date in its first line or its name; type its date (YYYY-MM-DD) as "
               "answers.{fact}.date")
PROGRAM_NOT_FOUND = ("the program {program} is in no folder of the search list; a folder is put on the list only by your "
                     "naming it in your settings file, {settings}")
DISPROVED_BEFORE_GO = "Refused: a value this run holds as safe may not be shown. No go was recorded and no run is open; look again."
# RUN-7's `in` for a shortcut's line (A55): his login zsh finds a command of that name, so the look stops and names it.
SHORTCUT_NAME_TAKEN = ("the shortcut's name is taken: a program, an alias, a shell function, a builtin or a reserved word of that "
                       "name, as your login shell holds it: row {row}")
# RUN-5's two stops at the look's finding of the key's earlier runs (the owner's ruling A57; A59, resting on it): each
# says which in fixed words and where the run directories are kept, and names no directory.
FIRST_RECORD_UNREADABLE = ("a run directory's first journal record cannot be read, so the look cannot tell whose run it is; "
                           "nothing is done until you mend that directory or move it")
RUNS_UNLISTABLE = ("the folder that holds the run directories cannot be listed, so the look cannot tell which runs are this "
                   "project's; nothing is done until you mend that folder")
RUNS_KEPT_AT = "the run directories are kept at: "
# EV-7's two stops of a restore's look, each resting on GOV-1 (A65; A70): no retiring run among the key's earlier runs,
# and two retirements whose records of their opening carry the latest time of go (A68).
NO_RETIRING_RUN = "no retiring run of the project is found, so a restore has nothing to build its plan from; nothing is done"
RETIREMENTS_AT_ONE_TIME = ("two retirements of the project carry the same time of go, so the look cannot tell which is the "
                           "latest; nothing is done")
# EV-7's stop of a restore's look (batch 30, resting on RUN-3's words and EV-7's): a retirement of the key is open and the
# latest sunset by the clock is another run, which only a clock set back can make.
OPEN_RETIREMENT_NOT_LATEST = ("an open retirement of the project is not its latest by the clock, so a restore's go could not "
                              "close it; nothing is closed and nothing is planned; resume or close that retirement first")
# EV-5 (batch 30): an operation of the retiring run's manifest in force that has no final record in its journal.
NOT_RUN_TO_ITS_END = "it was not run to its end, and no way back is on record for it"
# RUN-5's bound (batch 27, resting on GOV-1): the keys a look holds would make its run's record of its opening longer than
# the most a look reads of a first record.
TOO_MANY_NAMES = ("the project has more names than one run can be opened under; nothing is done")
# RUN-2's stop in a re-plan (the owner's ruling A72): its alias reads show a name form whose key the run does not hold.
NEW_NAME_IN_REPLAN = ("the project now shows another name, which this run was not opened under; the private file that holds "
                      "it: {path}; the ways on: close this run, then summon again giving all the names")
# RUN-2 and RUN-9 at the go of a first look an earlier invocation made (the owner's rulings A76 and A79): the go holds a key
# its look did not hold, or fewer keys than its manifest records; no go is recorded and no run is opened.
NEW_NAME_AT_GO = ("the project now shows another name, which its look did not hold; no go was recorded and no run is open; "
                  "the private file that holds it: {path}; summon again to make a new look that reads that name")
NAME_GONE_AT_GO = ("the project no longer shows a name its look showed; no go was recorded and no run is open; the private "
                   "file that holds it: {path}; summon again to make a new look under the names the project now shows")
# RUN-2's part (c) (resting on A72): a summons that continues a run carries a name whose key that run is not open under.
NOT_OPEN_UNDER_NAME = ("Refused: the run is not open under a name this summons gave. Nothing was changed. Summon again with the "
                       "run's own names, or close the run and summon anew under all the names.")
BUILD_FAILED = "The manifest's build failed; nothing was written of it. Each finding:"
NO_FORM_LINE = "Stopped: a status occurred that no form has a line for, so no form that lists operations could be built: "
CLOSE_WORD_NEEDED = "No word to close was given: nothing was recorded and the run is as it stood."
NEW_PLAN_AWAITS = "A new plan of this run awaits your go; nothing is done under the old one. Give your go on the new manifest, or re-plan again."
UNCONFIRMED_NO_REPLAN = "The run's last record is at its place and unconfirmed: the ways on are resume and close. No new plan was made."
