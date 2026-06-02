#!/usr/bin/env python3
"""Compact static terminal 'stamp' for sunset/sunrise. Usage: sun_stamp.py [set|rise]
One colored ANSI scene (no motion), run-length encoded to stay small so it
renders cleanly even when output is captured. Pair with afplay for sound."""
import sys, math

RISE = (sys.argv[1] if len(sys.argv) > 1 else 'set').lower() == 'rise'
W, H = 42, 9

def lerp(a, b, t): return a + (b - a) * t
def lerp3(c1, c2, t): return [int(lerp(c1[i], c2[i], t)) for i in range(3)]
def bg(c): return f"\033[48;2;{c[0]};{c[1]};{c[2]}m"
RESET = "\033[0m"

if RISE:                                   # dawn: sun low-left, climbing
    TOP, HOR = [20, 24, 60], [255, 200, 120]; sx, sy = 0.22 * W, 0.74 * H
else:                                      # dusk: sun low-right, setting
    TOP, HOR = [40, 30, 78], [248, 150, 86]; sx, sy = 0.78 * W, 0.72 * H

out = []
for y in range(H):
    sky = lerp3(TOP, HOR, y / (H - 1))
    cur, row = None, []
    for x in range(W):
        d = math.hypot((x - sx) / 1.8, y - sy)
        if d < 2.4:
            col = lerp3([255, 250, 222], [255, 168, 56], d / 2.4)
        elif d < 3.6:
            col = lerp3([255, 198, 108], sky, (d - 2.4) / 1.2)
        else:
            col = sky
        if col != cur:
            row.append(bg(col)); cur = col
        row.append(" ")
    out.append("".join(row) + RESET)

banner = "  \033[1;38;2;255;196;90m" + ("S U N R I S E" if RISE else "S U N S E T") + RESET
sys.stdout.write("\n".join(out) + "\n" + banner + "\n")
