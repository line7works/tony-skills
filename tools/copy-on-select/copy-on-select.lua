-- copy-on-select.lua
--
-- System-wide copy-on-select for macOS, via Hammerspoon. Highlight text in
-- (almost) any app with the mouse and it lands on the clipboard, no Cmd+C.
-- macOS has no native toggle for this; iTerm2 builds its own. This gives the
-- same behavior everywhere else.
--
-- Two layers:
--   1. Read the real selection via the Accessibility API (clean, no side
--      effects). Works in native views (iMessage). Measured 2026-07-16: it does
--      NOT work in Mail or Chrome, whose web views never expose AXSelectedText
--      anywhere in the ancestor chain, so layer 2 is what actually carries
--      those apps.
--   2. If AX comes up empty but the gesture was a real text drag, send Cmd+C.
--
-- Layer 2 is gated hard, because a stray Cmd+C is not harmless: it beeps in
-- Mail and pops a "copy this event?" dialog in Fantastical. Measured before
-- gating, it fired on 38% of ALL mouse-ups. The gates, and the misfire each
-- one kills:
--   * Sample mouse-up position synchronously, not in the deferred timer. The
--     timer samples 20ms after release, so a click followed by a fast mouse
--     move read as a 30-120px "drag" -- this was the Mail sidebar ping.
--   * Require the frontmost window to be unmoved and unresized. Dragging a
--     window by its title bar is a long, genuine drag over text-ish elements;
--     the window moving is what distinguishes it. This was the Fantastical and
--     Mail title-bar ping.
--   * Require the gesture to stay in one window. Text selection never crosses
--     windows.
-- Note element ROLE is deliberately not used as a gate: AXStaticText and
-- AXTextArea both appear on real selections AND on window drags, so it does
-- not separate the cases.
--
-- Install and dependencies: see README.md (Hammerspoon + Accessibility grant).

local ax = require("hs.axuielement")

local dragThreshold = 4 -- px of movement before a gesture counts as a drag

local downPos, upPos, downWinId, downFrame = nil, nil, nil, nil

local function frameOf(win)
  if not win then return nil end
  local ok, f = pcall(function() return win:frame() end)
  if not ok or not f then return nil end
  return { x = f.x, y = f.y, w = f.w, h = f.h }
end

-- nil frames count as "not the same", so an unreadable window suppresses the
-- fallback rather than firing it blind.
local function sameFrame(a, b)
  if not a or not b then return false end
  return a.x == b.x and a.y == b.y and a.w == b.w and a.h == b.h
end

-- Walk up from an element looking for a non-empty AXSelectedText.
local function selectedTextFrom(element, depth)
  if not element or depth > 6 then return nil end
  local ok, sel = pcall(function() return element:attributeValue("AXSelectedText") end)
  if ok and type(sel) == "string" and sel ~= "" then return sel end
  local parent = element:attributeValue("AXParent")
  return selectedTextFrom(parent, depth + 1)
end

local function readSelectionViaAX()
  local sw = ax.systemWideElement()
  local focused = sw:attributeValue("AXFocusedUIElement")
  local sel = selectedTextFrom(focused, 0)
  if sel then return sel end

  local pos = hs.mouse.absolutePosition()
  local underMouse = ax.systemElementAtPosition(pos.x, pos.y)
  return selectedTextFrom(underMouse, 0)
end

local function handleMouseUp()
  local sel = readSelectionViaAX()
  if sel then
    hs.pasteboard.setContents(sel)
    return
  end

  if not (downPos and upPos) then return end

  local dx, dy = upPos.x - downPos.x, upPos.y - downPos.y
  if (dx * dx + dy * dy) < (dragThreshold * dragThreshold) then return end

  local win = hs.window.frontmostWindow()
  local id = win and win:id() or nil
  if id == nil or id ~= downWinId then return end
  if not sameFrame(frameOf(win), downFrame) then return end

  hs.eventtap.keyStroke({ "cmd" }, "c")
end

-- Kept as globals on purpose: locals would be garbage-collected and the taps
-- would silently stop firing. Prefixed to avoid clashing with other config.
copyOnSelectDown = hs.eventtap.new({ hs.eventtap.event.types.leftMouseDown }, function()
  downPos = hs.mouse.absolutePosition()
  local win = hs.window.frontmostWindow()
  downWinId = win and win:id() or nil
  downFrame = frameOf(win)
  return false
end)
copyOnSelectDown:start()

copyOnSelectUp = hs.eventtap.new({ hs.eventtap.event.types.leftMouseUp }, function()
  upPos = hs.mouse.absolutePosition() -- sync: the deferred timer would read it late
  hs.timer.doAfter(0.02, handleMouseUp)
  return false
end)
copyOnSelectUp:start()

hs.alert.show("Copy-on-select active")
