# L4-credentials: cases

Family L4 of the E16 seeded cases (lane contract section 12, row "L4 credentials"; the lifecycle frame, slice 1). 11 cases, ids exact. Facts only: what each case holds. Nothing here states an outcome.

Build: `python3 build.py --out <dir>`. `../observe.py --out <dir> --all` drives each case and runs the scan of the frame's SEC-11 over the fixture home, both output streams and the fakes' records.

## Shared shape

The reference run's eight fake rows, with three more: a pull of env values into a new file (a build whose builder is the fake hosting tool, pointed at staging), a keep of the fake database (the fake dump tool, handed the connection in a private password file), and a change whose one request returns a credential in a secret field. A canary built when the case is built stands in every source: the session's hosting token; the password of the connection address in the project's env file; the value the fake hosting tool writes into the pulled env file; the data in the fake dump; a line of the owner's shortcut file. Every value a fake issues during the run (ids, the credential) is recorded by the fake. Steps: a first look, the go, and where named a status summons or a resume.

## L4-01-clean

Nothing planted.

## L4-02-a-fake-fails-echoing-it

The fake git tool's compare-and-swap exits with an error, writing a canary to its error text whole, in part, in base64 and split across writes, and to its standard output.

## L4-03-a-fake-writes-it-to-its-own-log

The fake hosting tool's create writes a canary into a log file in its own folder.

## L4-04-a-kill-mid-call

The go is killed while the fake dump tool's child is running; a resume follows.

## L4-05-a-missing-tool

The session's path does not hold the fake tools.

## L4-06-an-expired-token

The fake hosting tool's create exits with the status its declaration does not list, answering kind `auth`.

## L4-07-an-empty-env-pull

The fake hosting tool writes an empty env file.

## L4-08-a-half-env-pull

The fake hosting tool writes one of the env file's two lines.

## L4-09-a-malformed-answer

The fake hosting tool's credential request answers with a cut-off document.

## L4-10-a-linked-output-path

After the look, a symbolic link is planted at the place the pulled env file is to be published, pointing at a file elsewhere in the home.

## L4-11-a-debug-variable-in-the-session

The session holds a debug variable of the fake hosting tool and a general one.

## Not built as cases

A redirect (the frame makes no request of its own to a host in this slice), a full disk, and an exception inside the tool (a test, `test_cli`, plants one).
