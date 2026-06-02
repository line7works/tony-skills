#!/usr/bin/env python3
"""Generate the sunset/sunrise audio cues as dependency-free 16-bit WAVs.
rise.wav = ascending crescendo + bright burst chord.
set.wav  = descending decrescendo into a low fade.
Run: python3 make-sounds.py  (writes rise.wav + set.wav next to this script)."""
import wave, struct, math, os

SR = 44100
D = os.path.dirname(os.path.abspath(__file__))

NOTE = {'C4':261.63,'D4':293.66,'E4':329.63,'F4':349.23,'G4':392.00,'A4':440.00,
        'B4':493.88,'C5':523.25,'D5':587.33,'E5':659.25,'G5':783.99,'C6':1046.50}

def envelope(i, n, attack=0.012, release=0.12):
    t, dur = i / SR, n / SR
    if t < attack:
        return t / attack
    if t > dur - release:
        return max(0.0, (dur - t) / release)
    return 1.0

def tone(freq, dur, vol):
    n = int(SR * dur)
    out = []
    for i in range(n):
        t = i / SR
        s = math.sin(2*math.pi*freq*t) * 0.82 + math.sin(2*math.pi*freq*2*t) * 0.12
        out.append(s * vol * envelope(i, n))
    return out

def silence(dur):
    return [0.0] * int(SR * dur)

def write_wav(name, samples):
    with wave.open(os.path.join(D, name), 'w') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        frames = bytearray()
        for s in samples:
            frames += struct.pack('<h', int(max(-1.0, min(1.0, s)) * 32767))
        w.writeframes(bytes(frames))

# --- SUNRISE: ascending crescendo, then a bright swelling chord ("burst") ---
rise = []
for nm, d, v in [('C4',0.26,0.22), ('E4',0.26,0.30), ('G4',0.26,0.40), ('C5',0.30,0.50)]:
    rise += tone(NOTE[nm], d, v)
burst_n = int(SR * 0.85)
for i in range(burst_n):
    t = i / SR
    swell = min(1.0, t / 0.5)
    s = (math.sin(2*math.pi*NOTE['C5']*t) + math.sin(2*math.pi*NOTE['E5']*t) + math.sin(2*math.pi*NOTE['G5']*t)) / 3.0
    rise.append(s * 0.55 * swell * envelope(i, burst_n, attack=0.02, release=0.32))
write_wav('rise.wav', rise)

# --- SUNSET: descending decrescendo into a soft low fade ---
sset = []
for nm, d, v in [('E5',0.30,0.45), ('C5',0.30,0.38), ('A4',0.34,0.30), ('F4',0.52,0.22)]:
    sset += tone(NOTE[nm], d, v)
    sset += silence(0.04)
sset += tone(NOTE['C4'], 0.75, 0.18)
write_wav('set.wav', sset)

print("wrote", os.path.join(D, 'rise.wav'), "and", os.path.join(D, 'set.wav'))
