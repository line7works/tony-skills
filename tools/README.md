# Tony Tools

Machine-level tools and configs that are **not** Claude Code skills, so they
live outside `plugins/` and are not listed in `.claude-plugin/marketplace.json`.
These are things like macOS automations, dotfiles, and standalone scripts:
setup you copy onto a Mac directly, not something Claude Code installs or runs.

Each tool is a self-contained folder with its own `README.md` covering what it
is, its dependencies, and how to install it.

## Tools

- **[copy-on-select](copy-on-select/)** — system-wide highlight-to-clipboard on
  macOS via Hammerspoon. Select text with the mouse in almost any app (Mail,
  Chrome, iMessage, ...) and it is copied automatically, no `Cmd+C`.

## Conventions

- One folder per tool, named for the tool.
- Every tool folder has a `README.md` (what / why / dependencies / install /
  caveats).
- Keep install steps copy-pasteable and note any manual step (like an
  Accessibility grant) that can't be automated.
- New-Mac setup: install the tools here alongside the terminal/shell setup.
