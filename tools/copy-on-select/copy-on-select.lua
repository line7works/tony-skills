-- copy-on-select.lua
--
-- System-wide copy-on-select for macOS, via Hammerspoon. Highlight text in
-- (almost) any app with the mouse and it lands on the clipboard, no Cmd+C.
-- macOS has no native toggle for this; iTerm2 builds its own. This gives the
-- same behavior everywhere else.
--
-- Two layers:
--   1. Read the real selection via the Accessibility API (clean, no side
--      effects). Checks the focused element AND the element under the mouse,
--      walking up parents to catch WebKit views (Apple Mail, etc.), whose
--      selection the focused element alone does not expose.
--   2. If AX can't read a selection but the gesture was a real drag, fall back
--      to sending Cmd+C. Plain clicks never trigger the fallback, so an
--      ordinary click never clobbers the clipboard.
--
-- Install and dependencies: see README.md (Hammerspoon + Accessibility grant).

local ax = require("hs.axuielement")

local dragThreshold = 4 -- px of movement before a gesture counts as a drag
local mouseDownPos = nil

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

  -- Fallback: only fire Cmd+C when this was an actual drag gesture.
  if mouseDownPos then
    local up = hs.mouse.absolutePosition()
    local dx, dy = up.x - mouseDownPos.x, up.y - mouseDownPos.y
    if (dx * dx + dy * dy) >= (dragThreshold * dragThreshold) then
      hs.eventtap.keyStroke({ "cmd" }, "c")
    end
  end
end

-- Kept as globals on purpose: locals would be garbage-collected and the taps
-- would silently stop firing. Prefixed to avoid clashing with other config.
copyOnSelectDown = hs.eventtap.new({ hs.eventtap.event.types.leftMouseDown }, function()
  mouseDownPos = hs.mouse.absolutePosition()
  return false
end)
copyOnSelectDown:start()

copyOnSelectUp = hs.eventtap.new({ hs.eventtap.event.types.leftMouseUp }, function()
  hs.timer.doAfter(0.02, handleMouseUp)
  return false
end)
copyOnSelectUp:start()

hs.alert.show("Copy-on-select active")
