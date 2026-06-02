#!/usr/bin/env python3
"""Single-line terminal cue for sunset/sunrise. Usage: sun_bar.py [set|rise]
Uses half-block chars (one text cell = two stacked pixels) so the whole scene
plus label fits on ONE line, which never trips Claude Code's output fold."""
import sys

RISE = (sys.argv[1] if len(sys.argv) > 1 else 'set').lower() == 'rise'
W = 28

def lerp3(c1, c2, t): return [int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3)]
def dark(c, k=0.78): return [int(v * k) for v in c]
def cell(top, bot): return f"\033[38;2;{top[0]};{top[1]};{top[2]};48;2;{bot[0]};{bot[1]};{bot[2]}m▀"
RESET = "\033[0m"

if RISE:
    L, R, sunx = [255, 206, 132], [120, 170, 235], int(0.16 * W)   # dawn, sun left
else:
    L, R, sunx = [74, 92, 150], [245, 150, 80], int(0.84 * W)      # dusk, sun right

cells = []
for x in range(W):
    sky = lerp3(L, R, x / (W - 1))
    top, bot = sky, dark(sky)
    if abs(x - sunx) <= 1:                       # sun core (bright, slight shading)
        top, bot = [255, 242, 204], [255, 178, 86]
    elif abs(x - sunx) == 2:                      # sun glow
        glow = lerp3([255, 200, 116], sky, 0.5)
        top, bot = glow, dark(glow, 0.85)
    cells.append(cell(top, bot))

bar = "".join(cells) + RESET
glyph = "\033[38;2;255;210;120m☀\033[0m"
word = "\033[1;38;2;255;196;90m" + ("S U N R I S E" if RISE else "S U N S E T") + RESET
sys.stdout.write(f"{bar}  {glyph} {word}\n")
