"""Original Bollywood / bhangra-style soundtrack for the launch film (24 s, 44.1 kHz stereo).

Standard library only. All instruments are synthesized (no samples, no copyrighted material):
dhol (dagga + tilli), tumbi, sitar and bansuri via Karplus-Strong / additive synthesis,
tabla, chimta, claps and a tanpura drone. Key: D (Sa = D), Bhairav-flavoured scale.

Sections follow launch.html:
  0.0 - 3.0   tanpura drone + rising sitar arpeggio + riser
  3.0 - 11.4  dhol chaal groove, tumbi riff, claps, bass
  11.4 - 16.2 groove + sitar lead melody
  16.2 - 20.6 breakdown: bansuri, tanpura, soft tabla
  20.6 - 24.0 full groove, tihai (3x) landing on sam at 23.4, fade out
Writes soundtrack.wav next to this file (the file render.mjs picks up).
"""

import math
import random
import struct
import wave
from array import array
from pathlib import Path

SR = 44100
DUR = 24.0
N = int(SR * DUR)
BPM = 100
BEAT = 60 / BPM            # 0.6 s
TRIP = BEAT / 3            # triplet 8th: bhangra feel
SA = 146.83                # D3
SCALE = [0, 1, 4, 5, 7, 8, 11, 12]   # Sa re Ga ma Pa dha Ni Sa' (Bhairav)

rnd = random.Random(11)
L = array('d', bytes(8 * N))
R = array('d', bytes(8 * N))


def hz(semitones, octave=0):
    return SA * 2 ** (octave + semitones / 12)


def add(t0, samples, gain=1.0, pan=0.0):
    """Mix a mono sample list into the stereo bus at time t0 (pan -1 left .. +1 right)."""
    start = int(t0 * SR)
    gl = gain * math.cos((pan + 1) * math.pi / 4)
    gr = gain * math.sin((pan + 1) * math.pi / 4)
    for i, s in enumerate(samples):
        j = start + i
        if 0 <= j < N:
            L[j] += s * gl
            R[j] += s * gr


# ---------------------------------------------------------------- instruments
def dhol_bass(strength=1.0):
    n = int(0.45 * SR)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / SR
        f = 58 + 70 * math.exp(-t * 28)
        ph += 2 * math.pi * f / SR
        click = rnd.uniform(-1, 1) * math.exp(-t * 180) * 0.35
        out.append((math.sin(ph) * math.exp(-t * 7) + click) * strength)
    return out


def dhol_treble(strength=1.0):
    n = int(0.16 * SR)
    out = []
    lp = 0.0
    for i in range(n):
        t = i / SR
        lp += (rnd.uniform(-1, 1) - lp) * 0.55
        tone = math.sin(2 * math.pi * 410 * t) * math.exp(-t * 30)
        out.append((0.8 * lp * math.exp(-t * 45) + 0.6 * tone) * strength)
    return out


def tabla_na():
    n = int(0.35 * SR)
    return [(math.sin(2 * math.pi * 523 * i / SR) + 0.5 * math.sin(2 * math.pi * 1046 * i / SR)
             + 0.25 * math.sin(2 * math.pi * 1569 * i / SR)) * math.exp(-i / SR * 11) * 0.5 for i in range(n)]


def tabla_ge():
    n = int(0.5 * SR)
    out, ph = [], 0.0
    for i in range(n):
        t = i / SR
        ph += 2 * math.pi * (85 + 40 * (1 - math.exp(-t * 8))) / SR   # bayan pitch bend upward
        out.append(math.sin(ph) * math.exp(-t * 5))
    return out


def clap():
    n = int(0.2 * SR)
    out, lp = [], 0.0
    for i in range(n):
        t = i / SR
        lp += (rnd.uniform(-1, 1) - lp) * 0.7
        burst = sum(math.exp(-max(0.0, t - k * 0.011) * 60) * (t >= k * 0.011) for k in range(3)) / 3
        out.append(lp * burst)
    return out


def chimta():
    n = int(0.12 * SR)
    freqs = (3100, 4270, 5530, 6810)
    return [sum(math.sin(2 * math.pi * f * i / SR) for f in freqs) / 4 * math.exp(-i / SR * 40) for i in range(n)]


def pluck(freq, dur, decay=0.996, bright=0.5, buzz=0.0):
    """Karplus-Strong string with fractional delay; buzz adds a sitar-like jawari rasp."""
    n = int(dur * SR)
    p = SR / freq - 0.5
    li = int(p)
    fr = p - li
    size = li + 2
    buf = [rnd.uniform(-1, 1) for _ in range(size)]
    # soften the excitation for less bright instruments
    for _ in range(int((1 - bright) * 4)):
        buf = [(buf[k] + buf[k - 1]) * 0.5 for k in range(size)]
    out = []
    hist = buf[:]
    idx = 0
    for i in range(n):
        a = hist[(idx - li) % size]
        b = hist[(idx - li - 1) % size]
        y = decay * ((1 - fr) * a + fr * b)
        y = 0.5 * (y + hist[(idx - 1) % size]) if bright < 0.9 else y
        hist[idx % size] = y
        idx += 1
        s = y
        if buzz:
            s = s + buzz * (abs(s) * s * 3 - s * 0.3)
        env = min(1.0, i / 40)
        out.append(s * env)
    return out


def bansuri(freq, dur, glide_from=None):
    n = int(dur * SR)
    out, ph, lp = [], 0.0, 0.0
    for i in range(n):
        t = i / SR
        f = freq
        if glide_from is not None:
            f = glide_from + (freq - glide_from) * min(1.0, t / 0.18)   # meend
        f *= 1 + 0.008 * math.sin(2 * math.pi * 5.3 * t) * min(1.0, t / 0.4)
        ph += 2 * math.pi * f / SR
        lp += (rnd.uniform(-1, 1) - lp) * 0.1
        env = min(1.0, t / 0.07) * min(1.0, (dur - t) / 0.12)
        out.append((math.sin(ph) + 0.18 * math.sin(2 * ph) + 0.06 * math.sin(3 * ph) + 0.35 * lp) * env)
    return out


def bass(freq, dur):
    n = int(dur * SR)
    return [(math.sin(2 * math.pi * freq * i / SR) + 0.3 * math.sin(4 * math.pi * freq * i / SR))
            * min(1.0, i / 200) * math.exp(-i / SR * 3) for i in range(n)]


# pre-render repeated sounds once
BASS_HIT, TREB, NA, GE, CLAP, CHIMTA = dhol_bass(), dhol_treble(), tabla_na(), tabla_ge(), clap(), chimta()


def tanpura(t0, t1, gain):
    """Drone on Pa - Sa' - Sa' - Sa, one pluck per ~0.6 s with long tails."""
    seq = [hz(7, -1), hz(0), hz(0), hz(0, -1)]
    t, k = t0, 0
    while t < t1:
        add(t, pluck(seq[k % 4], 2.6, decay=0.9985, bright=0.3, buzz=0.35), gain, pan=-0.2 + 0.4 * (k % 2))
        t += 0.6
        k += 1


def chaal(t0, t1, gain=1.0, claps=True):
    """Bhangra dhol chaal on a triplet grid: DHA . na | DHA . na, with fills on beat 4."""
    beat = 0
    t = t0
    while t < t1 - 1e-6:
        add(t, BASS_HIT, 0.9 * gain * (1.0 if beat % 2 == 0 else 0.75))
        add(t + 2 * TRIP, TREB, 0.5 * gain, pan=0.25)
        if beat % 4 == 3:
            add(t + TRIP, TREB, 0.35 * gain, pan=0.25)
            add(t + 2 * TRIP, BASS_HIT, 0.4 * gain)
        if claps and beat % 2 == 1:
            add(t, CLAP, 0.35 * gain, pan=-0.15)
        for k in range(3):
            add(t + k * TRIP, CHIMTA, (0.12 if k else 0.18) * gain, pan=0.5)
        beat += 1
        t += BEAT


def tumbi_riff(t0, t1, gain):
    # one bar of triplet 8ths (12 slots); semitones above Sa, one octave up (None = rest)
    riff = [12, 12, None, 13, 12, None, 11, None, 12, 8, 7, None]
    alt = [12, 12, None, 13, 16, None, 13, 12, None, 11, 12, None]
    t, k = t0, 0
    while t < t1 - 1e-6:
        pattern = riff if (k // 12) % 2 == 0 else alt
        note = pattern[k % 12]
        if note is not None:
            add(t, pluck(hz(note, 1), 0.35, decay=0.992, bright=1.0), gain, pan=0.45)
        t += TRIP
        k += 1


def bassline(t0, t1, gain):
    roots = [0, 0, 5, 7]
    t, k = t0, 0
    while t < t1 - 1e-6:
        f = hz(roots[(k // 4) % 4], -1)
        add(t, bass(f, BEAT * 0.9), gain)
        add(t + 2 * TRIP, bass(f * 2, TRIP * 0.9), gain * 0.5)
        t += BEAT
        k += 1


def sitar_line(t0, notes, gain):
    """notes: (semitones, beats) pairs on the beat grid."""
    t = t0
    for semi, beats in notes:
        if semi is not None:
            add(t, pluck(hz(semi, 1), beats * BEAT + 0.6, decay=0.9975, bright=0.8, buzz=0.5), gain, pan=-0.4)
        t += beats * BEAT


def riser(t0, t1, gain):
    n = int((t1 - t0) * SR)
    out, lp, ph = [], 0.0, 0.0
    for i in range(n):
        k = i / n
        lp += (rnd.uniform(-1, 1) - lp) * (0.03 + 0.5 * k * k)
        ph += 2 * math.pi * (150 + 1400 * k * k) / SR
        out.append((0.7 * lp + 0.15 * math.sin(ph)) * k * k)
    add(t0, out, gain)


def boom(t0, gain):
    add(t0, dhol_bass(1.3), gain)
    add(t0, GE, gain * 0.8)
    n = int(1.8 * SR)
    add(t0, [math.sin(2 * math.pi * (40 + 60 * math.exp(-i / SR * 10)) * i / SR) * math.exp(-i / SR * 2.2)
             for i in range(n)], gain * 0.8)


# ---------------------------------------------------------------- arrangement
def arrange():
    # intro: drone + rising sitar arpeggio + riser into the reveal
    tanpura(0.0, 3.0, 0.4)
    t = 0.3
    for k, semi in enumerate([0, 4, 5, 7, 8, 11, 12, 13, 16, 17, 19]):
        add(t, pluck(hz(semi, 1), 1.2, decay=0.997, bright=0.8, buzz=0.45), 0.6, pan=-0.3 + 0.06 * k)
        t += 0.24 - 0.012 * k
    riser(1.2, 3.0, 0.35)
    for k in range(6):                                  # dhol roll into the hit
        add(2.4 + k * 0.1, TREB, 0.2 + 0.08 * k)

    # reveal hit + groove
    boom(3.0, 1.0)
    chaal(3.0, 16.2)
    tumbi_riff(3.0 + 4 * BEAT, 16.2, 0.32)
    bassline(3.0, 16.2, 0.35)

    # sitar lead over the features scene (11.4 - 16.2 = 8 beats)
    sitar_line(11.4, [(7, 1), (8, 0.5), (7, 0.5), (4, 1), (5, 1),
                      (7, 0.5), (8, 0.5), (11, 0.5), (12, 0.5), (13, 1), (12, 1)], 0.6)

    # breakdown: bansuri over tanpura, soft tabla theka
    tanpura(16.2, 20.6, 0.2)
    add(16.2, bansuri(hz(7, 1), 1.1), 0.28)
    add(17.3, bansuri(hz(8, 1), 0.5, glide_from=hz(7, 1)), 0.28)
    add(17.8, bansuri(hz(7, 1), 0.6, glide_from=hz(8, 1)), 0.28)
    add(18.4, bansuri(hz(4, 1), 0.7), 0.28)
    add(19.1, bansuri(hz(5, 1), 0.5), 0.28)
    add(19.6, bansuri(hz(7, 1), 1.0, glide_from=hz(5, 1)), 0.28)
    t = 16.2
    k = 0
    while t < 20.2:
        add(t, GE if k % 3 == 0 else NA, 0.3 if k % 3 == 0 else 0.22, pan=0.1)
        t += TRIP * (2 if k % 3 == 2 else 1)
        k += 1
    riser(19.6, 20.6, 0.3)

    # end card: full groove, then tihai landing on sam at 23.4
    boom(20.6, 0.9)
    chaal(20.6, 22.1)
    tumbi_riff(20.6, 22.1, 0.3)
    bassline(20.6, 22.1, 0.35)
    for start in (22.16, 22.65, 23.14):
        for j in range(3):
            add(start + j * 0.13, BASS_HIT, 0.8)
            add(start + j * 0.13, TREB, 0.5)
            add(start + j * 0.13, pluck(hz(12, 1), 0.3, bright=1.0), 0.25, pan=0.45)
    boom(23.4, 1.0)
    add(23.4, pluck(hz(0, 1), 0.6, decay=0.998, bright=0.8, buzz=0.5), 0.5, pan=-0.3)


def main():
    arrange()
    peak = max(max(abs(x) for x in L), max(abs(x) for x in R)) or 1.0
    frames = bytearray()
    for i in range(N):
        t = i / SR
        fade = 1 - min(1.0, max(0.0, (t - 23.5) / 0.5))
        for ch in (L, R):
            s = math.tanh(2.4 * ch[i] / peak) / math.tanh(2.4) * 0.92 * fade
            frames += struct.pack('<h', int(s * 32767))
    out = Path(__file__).with_name('soundtrack.wav')
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))
    print(f'wrote {out}')


if __name__ == '__main__':
    main()
