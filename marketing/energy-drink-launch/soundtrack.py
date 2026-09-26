"""Synthesize the launch film soundtrack (24 s, 44.1 kHz stereo) with the standard library only.

Structure mirrors launch.html: a rising charge-up (0-3 s), an impact on the reveal (3 s),
a 128 BPM beat with bass through the features, a softer bed under the scan scene and a
final hit into the end card (20.6 s) before fading out.
"""

import math
import random
import struct
import wave
from pathlib import Path

SR = 44100
DUR = 24.0
BPM = 128
BEAT = 60 / BPM
N = int(SR * DUR)
rand = random.Random(3)


def env(x, a, b):
    return max(0.0, min(1.0, (x - a) / (b - a)))


def kick(dt):
    if dt < 0 or dt > 0.35:
        return 0.0
    phase = 2 * math.pi * (45 * dt + 110 * (1 - math.exp(-dt * 30)) / 30)
    return math.sin(phase) * math.exp(-dt * 9)


def impact(dt):
    if dt < 0 or dt > 2.5:
        return 0.0
    boom = math.sin(2 * math.pi * (38 * dt + 80 * (1 - math.exp(-dt * 12)) / 12)) * math.exp(-dt * 2.2)
    return boom


def main():
    frames = bytearray()
    noise_lp = 0.0
    for i in range(N):
        t = i / SR
        s = 0.0
        # charge-up riser: sweeping saw + filtered noise
        if t < 3.05:
            k = t / 3.0
            f = 80 + 900 * k * k
            saw = 2 * ((f * t) % 1) - 1
            noise_lp += (rand.uniform(-1, 1) - noise_lp) * (0.02 + 0.3 * k)
            s += (0.12 * saw + 0.35 * noise_lp) * k * k
        # reveal and end-card impacts
        s += 0.9 * impact(t - 3.0)
        s += 0.6 * impact(t - 20.6)
        # beat section
        if 3.0 <= t < 23.5:
            beat_t = (t - 3.0) % BEAT
            beat_idx = int((t - 3.0) / BEAT)
            scan = 16.2 <= t < 20.6
            s += (0.35 if scan else 0.75) * kick(beat_t)
            # off-beat hat
            hat_t = (t - 3.0 - BEAT / 2) % BEAT
            if hat_t < 0.05:
                s += 0.08 * rand.uniform(-1, 1) * math.exp(-hat_t * 90)
            # bassline (A minor-ish), 8th-note pluck
            notes = [55.0, 55.0, 65.41, 49.0]
            f = notes[(beat_idx // 4) % 4]
            e8 = (t - 3.0) % (BEAT / 2)
            bass = math.sin(2 * math.pi * f * t) + 0.4 * math.sin(4 * math.pi * f * t)
            s += (0.12 if scan else 0.22) * bass * math.exp(-e8 * 6)
            # pad
            pad_f = [220.0, 261.63, 329.63]
            s += 0.03 * sum(math.sin(2 * math.pi * pf * t) for pf in pad_f) * env(t, 3.0, 5.0)
        # fade out
        s *= 1 - env(t, 23.0, 24.0)
        s = math.tanh(s * 1.2) * 0.85
        v = int(max(-1.0, min(1.0, s)) * 32767)
        frames += struct.pack('<hh', v, v)
    out = Path(__file__).with_name('soundtrack.wav')
    with wave.open(str(out), 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(bytes(frames))
    print(f'wrote {out}')


if __name__ == '__main__':
    main()
