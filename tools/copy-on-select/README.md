# copy-on-select

System-wide **copy-on-select** for macOS. Highlight text with the mouse in
almost any app and it is copied to the clipboard automatically, no `Cmd+C`.
Paste with `Cmd+V` as usual.

macOS has no native setting for this. iTerm2 builds its own copy-on-select
(Settings → General → Selection → "Copy to pasteboard on selection"); this
brings the same behavior to the rest of the system with a small
[Hammerspoon](https://www.hammerspoon.org/) config.

## Dependencies

- **Hammerspoon** (`brew install --cask hammerspoon`)
- **Accessibility permission** granted to Hammerspoon (System Settings →
  Privacy & Security → Accessibility → toggle Hammerspoon on). Required so it
  can read selected text and post the `Cmd+C` fallback. This is a manual GUI
  step Apple does not allow to be automated.

## Install

Pick one of two ways.

**A. As your whole Hammerspoon config** (simplest, if you have no other
Hammerspoon setup):

```bash
brew install --cask hammerspoon
mkdir -p ~/.hammerspoon
cp ~/Developer/tony-skills/tools/copy-on-select/copy-on-select.lua ~/.hammerspoon/init.lua
open -a Hammerspoon   # then grant Accessibility when prompted
```

**B. As a module alongside other Hammerspoon config** (if your `init.lua`
already does other things):

```bash
cp ~/Developer/tony-skills/tools/copy-on-select/copy-on-select.lua ~/.hammerspoon/copy-on-select.lua
# then add this line to ~/.hammerspoon/init.lua:
#   require("copy-on-select")
```

Reload with the Hammerspoon menu-bar icon → **Reload Config**. You will see a
**"Copy-on-select active"** flash confirming it loaded. To have it running
after every reboot, enable **Launch Hammerspoon at login** in its Preferences.

## How it works

Two layers, so it works in stubborn apps without clobbering the clipboard:

1. **Accessibility read (default path).** On mouse-up it reads the real text
   selection via the Accessibility API, checking both the focused element and
   the element under the mouse and walking up a few parents. The parent walk is
   what catches WebKit views like Apple Mail, whose message body does not
   expose its selection through the focused element (which is usually the
   message list, not the reading pane). No side effects: if there is no
   selection, nothing is copied.

2. **Drag-detect `Cmd+C` fallback.** If step 1 can't read a selection but the
   gesture was a real drag (mouse moved past a small threshold between
   mouse-down and mouse-up), it sends `Cmd+C`. A plain click never moves far
   enough to trigger this, so ordinary clicks never touch the clipboard.

## Caveats

- **Mouse selection only.** Selecting with Shift+arrow keys does not auto-copy.
  Adding keyboard selection is possible but noisy, so it is intentionally left
  out.
- **Finder file drags.** Rubber-band drag-selecting *files* (not text) in
  Finder can trip the fallback and copy those files. Harmless (a copy, never a
  cut), just expected behavior worth knowing.

## Optional init niceties

Not part of the tool, but handy if this is your whole `init.lua`. Add near the
top to control Hammerspoon from the terminal and auto-reload on edits:

```lua
require("hs.ipc") -- enables: hs -c "hs.reload()"
configWatcher = hs.pathwatcher.new(os.getenv("HOME") .. "/.hammerspoon/", function()
  hs.reload()
end):start()
```

## Verified

Working in iMessage, Chrome, and Apple Mail on macOS (Darwin 25.x),
Hammerspoon 1.1.1.
