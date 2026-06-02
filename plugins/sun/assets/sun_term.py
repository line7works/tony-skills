#!/usr/bin/env python3
"""Terminal sun animation (truecolor ANSI pixel-art). Usage: sun_term.py [set|rise]
Draws a small sky grid with a sun arcing across it, redrawn in place each frame."""
import sys, math, time

RISE = (sys.argv[1] if len(sys.argv) > 1 else 'set').lower() == 'rise'
W, H, F = 50, 12, 22

def lerp(a, b, t): return a + (b - a) * t
def lerp3(c1, c2, t): return [lerp(c1[i], c2[i], t) for i in range(3)]
def ease(t): return t * t * (3 - 2 * t)
def bg(r, g, b): return f"\033[48;2;{int(r)};{int(g)};{int(b)}m"
RESET = "\033[0m"

# sky palettes: (top start->end), (horizon start->end)
if RISE:
    TOP = ([14, 14, 34], [110, 170, 235]); HOR = ([52, 28, 66], [255, 212, 142])
else:
    TOP = ([110, 170, 235], [14, 12, 30]); HOR = ([255, 200, 120], [62, 24, 60])

def frame(p):
    e = ease(p)
    if RISE:
        sx, sy = lerp(0.14, 0.5, e) * W, lerp(0.84, 0.16, math.sin(p * math.pi / 2)) * H
    else:
        sx, sy = lerp(0.5, 0.88, e) * W, lerp(0.16, 0.84, math.sin(p * math.pi / 2)) * H
    burst = RISE and p > 0.9
    tcol, hcol = lerp3(*TOP, p), lerp3(*HOR, p)
    rows = []
    for y in range(H):
        sky = lerp3(tcol, hcol, y / (H - 1))
        cells = []
        for x in range(W):
            d = math.hypot((x - sx) / 2.0, y - sy)   # /2 compensates cell aspect
            R = 2.5 + (1.8 if burst else 0)
            if d < R:
                cells.append(bg(*lerp3([255, 250, 222], [255, 168, 56], d / R)))
            elif d < R + 1.4:
                cells.append(bg(*lerp3([255, 198, 108], sky, (d - R) / 1.4)))
            else:
                cells.append(bg(*sky))
            cells.append(" ")
        rows.append("".join(cells) + RESET + "\033[K")
    return "\n".join(rows)

sys.stdout.write("\033[?25l")                 # hide cursor
for f in range(F):
    if f > 0:
        sys.stdout.write(f"\033[{H}A")        # move up to redraw in place
    sys.stdout.write("\r" + frame(f / (F - 1)) + "\n")
    sys.stdout.flush()
    time.sleep(0.10)
sys.stdout.write("\033[?25h")                 # show cursor
sys.stdout.write("\033[1m" + ("   S U N R I S E" if RISE else "   S U N S E T") + RESET + "\n")
sys.stdout.flush()
