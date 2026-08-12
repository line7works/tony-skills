# arcade-publish — findings ledger

**The code moved.** `arcade-publish` and its documentation now live at
`plugins/arcade/assets/` in this repo, bundled as the `arcade` plugin's asset so
the `/arcade` skill and the terminal command share one copy. Read
`plugins/arcade/assets/README.md` for what the tool is, how to install it, and
how it behaves.

`~/.local/bin/arcade-publish` symlinks to the new location. The command itself is
unchanged.

## Why this folder still exists

`punch-list.md` stays here on purpose. It is the **single consolidated findings
ledger** for the tool, covering every review pass since it was built. It was
split into two lists once before and the same bug was promptly re-reported as
new — so it does not move with the code, and no second ledger gets started
anywhere else.

Findings go in that one file, whatever directory the code happens to live in.
